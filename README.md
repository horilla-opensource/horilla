
# **Horilla 🦍** [![AGPL License](https://img.shields.io/badge/license-AGPL-blue.svg)](http://www.gnu.org/licenses/agpl-3.0)
Horilla is a Free and Open Source HRMS Software.

<img width="1470" alt="Screenshot 2024-03-15 at 3 05 20 PM" src="https://github.com/horilla-opensource/horilla/assets/131998600/1317bd0a-03a8-40be-8fb2-ecb655bb5c13">


## **Installation**
____
Horilla can be installed on your system by following the below commands.

You'll have to install python, django and the database you wish to use for the project as a prerequisites.

### **Python Installation**
___

**Ubuntu**

Ubuntu comes with Python pre-installed, but if you need to install a specific version or if Python is not installed, you can use the terminal to install it.

Open the terminal and type the following command:
```bash
  sudo apt-get install python3
```
This will install the latest version of Python 3.

To check if Python is installed correctly, type the following command:
```bash
python3 --version
```
This should output the version number of Python that you just installed.

**Windows**

To install Python on Windows, follow these steps:
1. Download the latest version of Python from the official website: https://www.python.org/downloads/windows/ .
2. Run the installer and select "Add Python to PATH" during the installation process.
3. Choose the installation directory and complete the installation process.
4. To check if Python is installed correctly, open the Command Prompt and type the following command:
```bash
python3 --version
```
This should output the version number of Python that you just installed.

**macOS**

macOS comes with Python pre-installed, but if you need to install a specific version or if Python is not installed, you can use Homebrew to install it.

Follow these steps:
1. Install Homebrew by running the following command in the terminal:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
2. Install Python by running the following command in the terminal:
```bash
brew install python
```
To check if Python is installed correctly, type the following command in the terminal:
```bash
python3 --version
```
This should output the version number of Python that you just installed.

Congratulations, you have successfully installed Python on Ubuntu, Windows, or macOS! You can now start using Python to build applications.


### **Installing Django**
___

Before installing Django, you must have Python installed on your machine.

To install Django, follow the following steps:
1. Create a virtual environment:

It is highly recommended to create a virtual environment before installing Django.

A virtual environment allows you to isolate your Python environment and avoid conflicts with other Python packages that may be installed on your machine.

To create a virtual environment, open the terminal and navigate to the directory where you want to create the environment. Then type the following command:
```bash
python -m venv myenv
```
This will create a new virtual environment named "myenv".

To activate the virtual environment, type the following command:
```bash
source myenv/bin/activate
```
This will activate the virtual environment and you should see the name of the environment in the terminal prompt.

>Note that to activate your virtual environment on Widows, you will need to run the following code below (See this <a href="https://docs.python.org/3/library/venv.html">link</a> to fully understand the differences between platforms):
```bash
 env/Scripts/activate.bat //In CMD
 env/Scripts/Activate.ps1 //In Powershel
 ```
2. Install Django:

With the virtual environment activated, you can now install Django using pip, the Python package manager. Type the following command:
```bash
pip install Django
```
This will download and install the latest stable version of Django.

3. Verify the installation:

To verify that Django is installed correctly, type the following command in the terminal:
```bash
python -m django --version
```
This should output the version number of Django that you just installed.

Congratulations, you have successfully installed Django on your machine!
You can now start building web applications using Django.

### **Installing Horilla**
___

For installing the Horilla, follow the following steps:
1. Clone the project repository from GitHub:
```bash
git clone https://github.com/horilla-opensource/horilla.git
```
2. Install the required dependencies using pip:

For installing the python dependencies required for the project, run the following command by going into the project directory.
 ```bash
 pip install -r requirements.txt
 ```
>If you face any issue with the installing the pycairo package in ubuntu or macos, please follow the following commands and try the requirements installation command after this command.
>>**Ubuntu**
>>```sudo apt-get install libcairo2-dev```
>>
>>**MacOS**
>>```brew install py3cairo```

>Run the requirement installation command again

3. Set up the database by running the following commands:
   _By default the test database will be loaded which will have demo data inside it. If you wish to start with a fresh database, you can either remove the TestDB_Horilla.sqlite3 from the project directory or change the name of the database inside the horilla/settings.py file. (You can configure different database based on your choice, of which configurations settings is given below in the documentation._
```bash
python manage.py makemigrations
python manage.py migrate
```
4. Create an admin employee account (use this command if you are starting with a fresh database, for the demo database there is already a Horilla admin user created with credentials _admin_ and _admin_ as username and password respectively).
```bash
python manage.py createhorillauser
```
>Note: createhorillauser is a similar command to createsuperuser in Django,  which creates an admin user along with a related admin employee into the database.

<br>
Enter the details asked for creating the admin user for the project.

5. Enabling the translations and breadcrumbs text
   ```bash
   python manage.py compilemessages
   ```

7. Running the project
To run the project locally, execute the following command:

```bash
python manage.py runserver
```
If everything is configured correctly, you should be able to access your Horilla app at http://localhost:8000.

>Note:
>>If you wish to run the Horilla application to any other port, you can specify the port number after the runserver command.

>>eg: *python  manage.py runserver <port_number>*

>Note:
>>By default a SQLite database will be setup for the project with demo data already loaded.

>>If you wish to start with a fresh database, remove the db.sqlite3 file from the project directory and run the migrate command followed by the createhorillauser command to start with a fresh database.

>>Or if you wish to change the database, refer the below section.

### **Database Setup**
___

By default an SQLite database will be setup for the project, incase you wish to change the database of your choice, please use the below reference to do the same.

**PostgreSQL**

To setup postgresql database for the project, first you have to install the PostgreSQL and its python package ***psycopg2*** .
1. Install the psycopg2 package using pip. This package is a PostgreSQL database adapter for Python.
```bash
pip install psycopg2
```
2. In the project settings file (settings.py), add the following database settings:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '<database_name>',
        'USER': '<database_user>',
        'PASSWORD': '<database_password>',
        'HOST': '<database_host>',
        'PORT': '<database_port>',
    }
}
```
Replace *<database_name>, <database_user>, <database_password>, <database_host>, and <database_port>* with your PostgreSQL database settings.

3. Run migrations to create the necessary database tables.
```bash
python manage.py makemigrations
python manage.py migrate
```
For more details:
[Django PostgreSQL Database](https://docs.djangoproject.com/en/4.2/ref/databases/#postgresql-notes)

**MySQL**

To configure a MySQL database in Django, follow these steps:
1. Install the ***mysqlclient*** package which will allow Django to interact with MySQL. You can install it using pip:
```bash
pip install mysqlclient
```
2. In the project settings file (settings.py), add the following database settings:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '<database_name>',
        'USER': '<database_user>',
        'PASSWORD': '<database_password>',
        'HOST': '<database_host>',
        'PORT': '<database_port>',
    }
}
```
Replace *<database_name>, <database_user>, <database_password>, <database_host>, and <database_port>* with the appropriate values for your MySQL installation.


3. Run migrations to create the necessary database tables.
```bash
python manage.py makemigrations
python manage.py migrate
```
For more details:
[Django MySQL Database](https://docs.djangoproject.com/en/4.2/ref/databases/#mysql-notes)

**MariaDB**

To configure a MariaDB database with Django, you can follow the same steps used for MySQL database configuration as shown above.
For more details:
[Django MariaDB Database](https://docs.djangoproject.com/en/4.2/ref/databases/#mariadb-notes)

**SQLite**

To configure a SQLite database with Django, you can follow these steps:
1. In the project settings file (settings.py), add the following database settings:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```
This will create a SQLite database in your project directory named db.sqlite3.



2. Run migrations to create the necessary database tables.
```bash
python manage.py makemigrations
python manage.py migrate
```
>*Note that SQLite has some limitations compared to other databases, so you may need to consider these limitations if you have a large amount of data or a high level of concurrency in your application.*

For more details:
[Django SQLite Database](https://docs.djangoproject.com/en/4.2/ref/databases/#sqlite-notes)

**Oracle**

To configure an Oracle database with Django, you can follow these steps:
1. Install the cx_Oracle package which will allow Django to interact with Oracle. You can install it using pip:
```bash
pip install cx_Oracle
```
2. In the project settings file (settings.py), add the following database settings:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.oracle',
        'NAME': '<database_name>',
        'USER': '<database_user>',
        'PASSWORD': '<database_password>',
        'HOST': '<database_host>',
        'PORT': '<database_port>',
    }
}
```
Replace *<database_name>, <database_user>, <database_password>, <database_host>, and <database_port>* with the appropriate values for your Oracle installation.


3. Run migrations to create the necessary database tables.
```bash
python manage.py makemigrations
python manage.py migrate
```
>*Note that Oracle has some specific requirements for its database setup, so you may need to consult Oracle's documentation for more information on how to set up your database correctly.*

For more details:
[Django Oracle Database](https://docs.djangoproject.com/en/4.2/ref/databases/#oracle-notes)


###  **Features**

- Recruitment
- Onboarding
- Employee
- Attendance
- Leave
- Asset
- Payroll
- Performance Management System

### **Roadmap**



- Calendar App - Development Under Process

- Project Management - Development Under Process

- Chat App - Development Under Process

- More to come.....

___
<br>

### **Laguages and Tools Used:**
<br>
<p align="left"> <a href="https://getbootstrap.com" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/bootstrap/bootstrap-plain-wordmark.svg" alt="bootstrap" width="40" height="40"/> </a> <a href="https://www.chartjs.org" target="_blank" rel="noreferrer"> <img src="https://www.chartjs.org/media/logo-title.svg" alt="chartjs" width="40" height="40"/> </a> <a href="https://www.w3schools.com/css/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/css3/css3-original-wordmark.svg" alt="css3" width="40" height="40"/> </a> <a href="https://www.djangoproject.com/" target="_blank" rel="noreferrer"> <img src="https://cdn.worldvectorlogo.com/logos/django.svg" alt="django" width="40" height="40"/> </a> <a href="https://git-scm.com/" target="_blank" rel="noreferrer"> <img src="https://www.vectorlogo.zone/logos/git-scm/git-scm-icon.svg" alt="git" width="40" height="40"/> </a> <a href="https://www.w3.org/html/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/html5/html5-original-wordmark.svg" alt="html5" width="40" height="40"/> </a> <a href="https://www.linux.org/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/linux/linux-original.svg" alt="linux" width="40" height="40"/> </a> <a href="https://www.mysql.com/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/mysql/mysql-original-wordmark.svg" alt="mysql" width="40" height="40"/> </a> <a href="https://www.oracle.com/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/oracle/oracle-original.svg" alt="oracle" width="40" height="40"/> </a> <a href="https://www.postgresql.org" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/postgresql/postgresql-original-wordmark.svg" alt="postgresql" width="40" height="40"/> </a> <a href="https://www.python.org" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="python" width="40" height="40"/> </a> <a href="https://www.sqlite.org/" target="_blank" rel="noreferrer"> <img src="https://www.vectorlogo.zone/logos/sqlite/sqlite-icon.svg" alt="sqlite" width="40" height="40"/> </a> </p>
<br>

___

### **AUTHORS**
[Cybrosys Technologies](https://www.cybrosys.com/)

### **ABOUT**
[Horilla](https://www.horilla.com/)
