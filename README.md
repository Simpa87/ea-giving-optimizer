# ea-giving-optimizer
Tool for running scenarios with different assumptions (returns, discounting, leaking money) to see 
total impact on lives saved over a lifetime.
The idea is to be able to model trade-offs with different assumptions. 
The app is online with interface and more descriptions at: 
https://share.streamlit.io/simoncelinder/ea-giving-optimizer/main/ea_giving_optimizer/app.py


## 1. Set up a virtualenv, activate it and install dependencies
```bash
python3 -m venv .env 
source .env/bin/activate
pip install -e .
```


## 2. If want to open the app / frontend locally
```bash
streamlit run ea_giving_optimizer/app.py
```


## 3. If want to explore in notebook
Having the virtualenv activated and being in the project directory, launch jupyter notebook and explore (e.g. check out the example notebook in ea_giving_optimizer)
```bash
jupyter notebook
```


## 4. If want to set up pytest for unit tests in Pycharm
- Having installed pytest from the dependencies, from the configuration panel up in the top right of Pycharm, select Edit configurations from the dropdown
- Click the + sign to add a new configuration and go to Python tests --> pytest
- In "Target:", select script path, and add the path for the tests folder (or specific script in it)
- Also select the right virtualenv for the project to run the tests in that window
- After Pycharm has updated, you should be able to run all tests for the script file at once (play button in top right panel), or run individual tests with a play button on the test function
