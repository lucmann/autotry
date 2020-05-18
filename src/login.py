#!/usr/bin/python

import os
import time
import json
import logging
import requests
import pytesseract
from retry import retry
from requests.exceptions import HTTPError
from io import BytesIO
from PIL import Image, ImageEnhance

HOST = ""
image_name = "vcode.jpg"
install_path = os.getenv('APPOINT_DBS_PATH', "/home/git")

dbs_file = install_path + "/autotry/doctors.json"
log_file = install_path + "/autotry/appoint.log"

logging.basicConfig(filename=log_file,
                    format='%(asctime)s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class Appointment:
    def __init__(self, host=HOST, doctor="", patient=""):
        self.session = requests.Session()
        self.host = host
        self.dbs = self.load_dbs()
        self.doctor = self.dbs['Doctors'][doctor]
        self.patient = self.dbs['Patients'][patient]
        self.urls = {
            "vcode": "/Account/GetValidateCode",
            "login": "/api/hbapi/account/login?hbsign=",
            "time": "/api/hbapi/standard/getconfirmappoint?hbsign=",
            "pay": "/api/hbapi/booking/clinicpay?hbsign=",
            "schm": "/api/hbapi/booking/searchdoctorappointments?hbsign="
        }

    def load_dbs(self):
        with open(dbs_file) as f:
            # infos is a dictionary
            return json.load(f)

    def get_full_url(self, url):
        full_url = self.host + url + "%d" % (time.time() * 1000)
        logger.info(full_url)

        return full_url

    def get_vcode(self):
        try:
            response = self.session.get(self.host + self.urls['vcode'])

            response.raise_for_status()

        except HTTPError as http_err:
            logger.error(f'HTTP error occured: {http_err}')

        except Exception as err:
            logger.error(f'Other error occured: {err}')

        else:
            try:
                image = Image.open(BytesIO(response.content))
            except IOError as io_err:
                logger.error(f'IO error occured: {io_err}')
            else:
                image = convert_img_mode(image, 'L')
                image = binarize(image)
                image.save(image_name)
                vcode = pytesseract.image_to_string(image_name, config='-l digits --psm 6 digits')
                logger.info(f"Verification Code {vcode}")

                return vcode

    @retry()
    def login(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        payload = {
            'LoginName': self.patient['LoginName'],
            'Password': self.patient['Password'],
            'VerifyCode': self.get_vcode()
        }

        response = self.session.post(self.get_full_url(self.urls['login']),
                                     headers=headers, data=payload)
        logger.info(response.json())

    def book(self):
        book_url = "/Appointment/ConfirmAppoint?ClinicLabelId={}&ClinicDate={}&NoonId={}&NoonText={}&HospitalGuid={" \
                   "}&SchmId={}".format(
            self.doctor['ClinicLabelId'],
            self.doctor['ClinicDate'],
            self.doctor['Noon'],
            self.doctor['NoonText'],
            self.dbs['HospitalGuid'],
            self.doctor['SchmId']
        )

        full_url = self.host + book_url

        headers = {'User-Agent': 'Mozilla/5.0'}
        payload = {
            'ClinicLabelId': self.doctor['ClinicLabelId'],
            'ClinicDate': self.doctor['ClinicDate'],
            'NoonId': self.doctor['Noon'],
            'NoonText': self.doctor['NoonText'],
            'HospitalGuid': self.dbs['HospitalGuid'],
            'SchmId': self.doctor['SchmId']
        }

        response = self.session.post(full_url, headers=headers, data=payload)

    def get_schmid(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        payload = {
            'DoctorId': self.doctor['DoctorId'],
        }

        response = self.session.post(self.get_full_url(self.urls['schm']),
                                     headers=headers, data=payload)

        result = response.json()
        logger.info(result)
        result_list = result['ResultData']
        schmid = result_list[-1]['Appointments'][-1]['SchmId']
        logger.info(schmid)
        return schmid

    def get_appoint_time(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        payload = {
            'ClinicDate': self.doctor['ClinicDate'],
            'ClinicLabelId': self.doctor['ClinicLabelId'],
            'NoonId': self.doctor['Noon'],
            'SchmId': self.doctor['SchmId']
        }

        response = self.session.post(self.get_full_url(self.urls['time']),
                                     headers=headers, data=payload)

        result = response.json()
        logger.info(result)
        return result['ResultData']['TimePartResponsesList']

    def pay(self, time_part):
        headers = {'User-Agent': 'Mozilla/5.0'}
        payload = {
            'IdCode': self.patient['IdCode'],
            'IdType': '0',
            'IsClinic': 'false',
            'ClinicDate': self.doctor['ClinicDate'],
            'ClinicLabelId': self.doctor['ClinicLabelId'],
            'Noon': self.doctor['Noon'],
            'SchmId': self.doctor['SchmId'],
            'PatientId': self.patient['PatientId'],
            'OperateType': self.dbs['OperateType'],
            'AppointmentId': self.dbs['AppointmentId'],
            'PayChannel': self.dbs['PayChannel'],
            'PayType': self.dbs['PayType'],
            'TimePart': time_part['StartTime'],
            'EndTimePart': time_part['EndTime']
        }

        response = self.session.post(self.get_full_url(self.urls['pay']),
                                     headers=headers, data=payload)

        result = response.json()
        logger.info(result)

        return result['ResultCode'] == 1


def opt_img_color(img, factor):
    return ImageEnhance.Color(img).enhance(factor)


def opt_img_contrast(img, factor):
    return ImageEnhance.Contrast(img).enhance(factor)


def convert_img_mode(img, mode):
    return img.convert(mode)


def binarize(img):
    threshold = 150
    table = []
    for i in range(256):
        if i < threshold:
            table.append(0)
        else:
            table.append(1)

    return img.point(table, "1")


if __name__ == "__main__":
    poor = Appointment()
    poor.login()
    poor.doctor['SchmId'] = poor.get_schmid()
    poor.book()
    timeparts = poor.get_appoint_time()
    for time_part in timeparts:
        if poor.pay(time_part):
            break;
