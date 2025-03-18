import os

basedir = os.path.abspath(os.path.dirname(__file__))  # Get base directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'office_management.db')
