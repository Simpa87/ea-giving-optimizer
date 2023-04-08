from setuptools import setup, find_packages

# Using requirements.txt for dependencies since Streamlit finds that file but not setup.py
setup(
    name='ea-giving-optimizer',
    version='0.0.1',
    description='Tool for running scenarios of giving over lifetime',
    url='https://github.com/simoncelinder/ea-giving-optimizer',
    author='Simon Celinder',
    author_email='simon.mindfulprofessionals@gmail.com',
    license='None',
    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'examples']),
    zip_safe=False
)
