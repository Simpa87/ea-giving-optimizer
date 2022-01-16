from setuptools import setup, find_packages

setup(
    name='ea-giving-optimizer',
    version='0.0.1',
    description='Tool for running scenarios of giving over lifetime',
    url='https://github.com/Simpa87/ea-giving-optimizer',
    author='Simon Celinder',
    author_email='simon.mindfulprofessionals@gmail.com',
    license='None',
    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'examples']),
    install_requires=[
        'numpy1.21.5',
        'pandas==1.3.5',
        'ipython==7.30.1',
        'notebook==6.4.6',
        'scipy==1.7.3',
        'pytest==6.2.5',
        'streamlit==1.3.1'
        'plotly==5.4.0',
        'cufflinks==0.17.3',
        'chart-studio==1.1.0'
    ],
    tests_require=['nose'],
    zip_safe=False
)
