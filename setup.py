from setuptools import find_packages, setup

setup(
    name='Keybase-Knowledge-Base',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'Flask-Breadcrumbs',
        'Flask-Cors',
        'Flask-Login',
        'Flask-Menu',
        'flask-paginate',
        'gunicorn',
        'numpy',
        'redis-om',
        'sentence-transformers',
        'shortuuid',
        'python-dotenv '
    ],
)