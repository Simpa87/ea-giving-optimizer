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
        'numpy',
        'pandas',
        'matplotlib',
        'seaborn',
        'scikit-learn',
        'optuna',
        'pulp',
        'ipython',
        'notebook',
        'pytest'
    ],
    tests_require=['nose'],
    zip_safe=False
)
