# Poloniex Trade Bot with Web Panel

## Overview


This is the crypto currency trading bot written on Python 3.6 with Web interface (Django).
Based on [CATEd](https://github.com/OnGridSystems/CATEd), 
but celery + channels + Django is too slow and too resource intensive 
combination. So, I separated it into two different parts -
web interface and background service. 

Main features:
* View the status of exchange accounts, transactions and orders on them;
* Configurable Strict and Soft trading;
* Keeping the balances of different tokens at the configured levels;

For working with Poloniex API used [poloniex](https://github.com/Aula13/poloniex), with some changes.


## Install

You need python3(written on 3.6), mysql-server.

Create python virtual env and activate it in your favorite way.

Clone project
```sh
git clone git@github.com:stahh/poloniex_trade_bot.git
```
Go to project dir
```sh
cd poloniex_trade_bot
```
Create mysql database
```sh
echo "create database poloniex_trade character set utf8;" | mysql -u root -p
```
Create tables
```sh
python manage.py makemigrations
```
```sh
python manage.py migrate
```
Load initial data with exchange
```sh
python manage.py loaddata dump.json
```

Create you own superuser with
```sh
python manage.py createsuperuser
```
* Input username and password
And runserver
```sh 
python manage.py runserver
```
Configure settings.py. 
* Set POLONIEX_API_KEY and POLONIEX_API_SECRET for poloniex
* Set TELEGRAM_TOKEN and CHANNEL for using telegram bot

**Add NEW api keys for use bot.**

To do this open http://127.0.0.1:8000/ in your browser, login and click red "plus" button in the lower right corner.
It's your web interface

For running trade bot
```shell script
cd ./async_bot
```
And run bot
```shell script
python daemon.py
```
**Please note: This is just a pet-project. You can use it at your own risk.**
