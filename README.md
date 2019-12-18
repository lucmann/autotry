# autotry
Autotry is a tiny tool to get appointed in some hospital website. It is written in python but requires tesseract-ocr 4.0 or above to work.


## Prerequisites
- fiddler
    * [binary install](https://www.telerik.com/download/fiddler)
- requests
    * pip install requests
- tesseract-ocr
    * sudo apt install tesseract-ocr
- Python Imaging Library(PIL)
    * pip install Pillow
- pytesseract
    * pip install pytesseract


## cron service on the WSL(ubuntu) in Windows 10

- Query services status

`service --status-all`

- Start cron service on the WSL

`sudo service cron start`

- Add cron task entry

`crontab -e`

Edit the user's cron task list file directly 

- List cron tasks

`crontab -l`

- How to check if the cron schedules your task

`cat /var/log/crontab.log`

Note that it requires configuration in the `/etc/rsyslog.d/50-default.conf` and restarting the rsyslog
service to take cron log in effect

`sudo service rsyslog restart`

- How to check the cron task execution log

`cat /var/spool/mail/$(whoami)`

Note that cron daemon will send the task execution details to the user's mailbox by default, which requires
the mail service is available on your system. if not, try

`sudo apt install postfix`

`sudo service postfix start`

