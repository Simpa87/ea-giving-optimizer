# ea-giving-optimizer
Tool for running scenarios with different assumptions (returns, discounting, leaking money) to see total impact on lives saved over a lifetime.
The idea is to be able to model trade-offs with different assumptions. The 
app is online with interface at: https://share.streamlit.io/simoncelinder/ea-giving-optimizer/main/ea_giving_optimizer/app.py

Example of assumptions that can be modelled:
- Interest on money saved to give more later (stock market return etc.)
- Cost of waiting
  - Existential risk compounding (nukes, global warming, AI, biotech etc.)
  - Though saving lives in the future might be as valuable as now, the problem of global suffering might be bigger now, making it bad to wait
  - Risk of "leaking" from intended giving to other causes (loans to relatives, inheritance etc., bigger amounts later "feeling more expensive", hence giving less)

<b>Feature ideas for the future</b><br>
 - Be able to set optimization constraints, e.g. need minimum amount X at age Y (apartment, retirement). Would currently need to be set by user as required cost of living for saving up the years before (implied savings).

<b>Other ideas</b><br>
- Could it be that one of the most high impact and low effort moral decisions is simply to write ones testament early in life, to solidify the decision to give and have a large share of savings go to EA if passing away, by default?
- Interesting article about discounting humanity into eternity with existential risk rates and estimating cost of waiting to give: https://forum.effectivealtruism.org/posts/3fmcNMrR8cktLnoYk/giving-now-vs-later-for-existential-risk-an-initial-approach


## 1. Set up a virtualenv and activate it
It is suggested to create a virtualenv for installing required dependencies in it

```bash
python3 -m venv .env 
source .env/bin/activate
```

## 2. Install dependencies
cd to root where setup.py is, and make sure the right virtualenv is activated
```bash
pip install -e .
```

## 3. Open notebook and explore
Having the virtualenv activated and being in the project directory, launch jupyter notebook and explore (e.g. check out the example notebook in ea_giving_optimizer)
```bash
jupyter notebook
```

## 4. If want to open the app / frontend
```bash
streamlit run ea_giving_optimizer/app.py
```

## Optional - Set up pytest for unit tests in Pycharm
- Having installed pytest from the dependencies, from the configuration panel up in the top right of Pycharm, select Edit configurations from the dropdown
- Click the + sign to add a new configuration and go to Python tests --> pytest
- In "Target:", select script path, and add the path for the tests folder (or specific script in it)
- Also select the right virtualenv for the project to run the tests in that window
- After Pycharm has updated, you should be able to run all tests for the script file at once (play button in top right panel), or run individual tests with a play button on the test function
