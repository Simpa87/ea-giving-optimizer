import numpy as np
import pandas as pd
import streamlit as st
from plotly import express as px
from scipy.optimize import linprog


# All helpers are put here since streamlit does not identify setup.py


class Config:

    def __init__(self,
                 # Just example data!

                 # General assumptions
                 current_age=30,
                 current_savings_k=0,
                 life_exp_years=80,
                 save_qa_life_cost_k=35,

                 # Per age
                 month_salary_k_per_age={30: 53, 40: 65, 45: 55, 65: 50, 66: 10},  # Lower from retirement
                 month_req_cost_k_per_age={30: 20, 65: 20, 66: 20},

                 # Marginal taxation
                 share_tax_per_k_salary={10: (1 - 8.2 / 10), 20: (1 - 16 / 20), 30: (1 - 24 / 30), 40: (1 - 31 / 40),
                                         50: (1 - 37 / 50), 60: (1 - 42 / 60), 80000: (1 - 52 / 80)},

                 # Return on savings e.g. stock market rate
                 return_rate_after_inflation=0.07,

                 # Cost of exponential risks compounding
                 existential_risk_discount_rate=0.0023,

                 # Leaking money to other causes
                 # E.g. dying and 50% legal inheritance
                 # Note that this leakage is applied for a certain age for the total giving result for that age
                 leak_multiplier_per_age={30: 0.95, 45: 0.8, 55: 0.75, 80: 0.5},
                 ):

        # Assert Consistency
        assert all((0 <= v <= 1) for v in share_tax_per_k_salary.values())
        assert max(share_tax_per_k_salary.keys()) >= max(month_salary_k_per_age.values()), \
            'Maximum share tax doesnt cover span of salaries'
        assert min(share_tax_per_k_salary.keys()) <= min(month_salary_k_per_age.values()), \
            'Minimum share tax doesnt cover span of salaries'
        assert all((0 <= v <= 1) for v in leak_multiplier_per_age.values())
        assert life_exp_years > current_age
        assert -0.1 <= return_rate_after_inflation <= 0.3
        assert 0 <= existential_risk_discount_rate <= 0.99

        self.life_exp_years = life_exp_years
        self.save_qa_life_cost_k = save_qa_life_cost_k
        self.net_return_mult = 1 + return_rate_after_inflation - existential_risk_discount_rate
        assert 0.01 <= self.net_return_mult <= 2  # Return multiplier can be < 1 after existential risk

        # Save for metadata e.g. prints on ffill
        self.leak_multiplier_per_age = leak_multiplier_per_age
        self.month_salary_k_per_age = month_salary_k_per_age
        self.month_req_cost_k_per_age = month_req_cost_k_per_age

        salary_per_age_df = self.interpolate_df_from_dict(
            month_salary_k_per_age,
            min_idx=current_age,
            max_idx=life_exp_years,
            col_name='salary_k'
        ).ffill()  # Forward fills pension until life_expectancy

        cost_per_age_df = self.interpolate_df_from_dict(
            month_req_cost_k_per_age,
            min_idx=current_age,
            max_idx=life_exp_years,
            col_name='req_cost'
        ).ffill()  # Assume continued at same level as last data point e.g. pension level

        salary_per_age_df.index.name = 'age'
        salary_per_age_df = salary_per_age_df.round(0)  # For integer join

        self.tax_per_salary_df = self.interpolate_df_from_dict(share_tax_per_k_salary,
                                                               min_idx=min(share_tax_per_k_salary.keys()),
                                                               max_idx=max(share_tax_per_k_salary.keys()),
                                                               col_name='share_tax',
                                                               step_size=1
                                                               )

        self.tax_per_salary_df.index.name = 'salary_k'
        df = pd.merge(left=salary_per_age_df.reset_index(),
                      right=self.tax_per_salary_df.reset_index(),
                      on='salary_k',
                      how='left')

        # Left join (map) interpolated cost per age
        df['req_cost_k_year'] = df['age'].map(cost_per_age_df.to_dict()['req_cost']) * 12

        # Leaking multiplier per age
        leak_mult_per_age_df = self.interpolate_df_from_dict(
            leak_multiplier_per_age,
            min_idx=min(leak_multiplier_per_age.keys()),
            max_idx=max(leak_multiplier_per_age.keys()),
            col_name='leak_multiplier',
        )

        # Left join (map) it
        df['leak_multiplier'] = df['age'].map(leak_mult_per_age_df.to_dict()['leak_multiplier'])

        # Only include cumulation and compounding from current age
        df = df.loc[df['age'] >= current_age]

        df['years'] = np.arange(len(df))
        df['compound_interest'] = self.net_return_mult ** df['years']  # After infl and exist risk
        df['salary_k_year'] = df['salary_k'] * 12
        df['salary_k_year_after_tax'] = (df['salary_k_year'] * (1 - df['share_tax'])).round(0)
        df['disposable_salary'] = (df['salary_k_year_after_tax'] - df['req_cost_k_year']).round(0)

        # Add current savings which are assumed already tax
        df.loc[df['age'] == current_age, 'disposable_salary'] += current_savings_k

        df['disposable_salary'] = df['disposable_salary'].ffill()

        df = df.fillna(0).set_index('age')
        self.df = df

        # Placeholders for result
        self.sum_given_m = None
        self.lives_saved = None

    def get_ffill_note(self):

        if (
                max(self.leak_multiplier_per_age.keys()) < self.life_exp_years or
                max(self.month_salary_k_per_age.keys()) < self.life_exp_years or
                max(self.month_req_cost_k_per_age.keys()) < self.life_exp_year
        ):
            return "One or some dictionaries had a lower max age than life_exp, the last value was " \
                   "hence forward-filled."
        else:
            return None

    def interpolate_df_from_dict(self, data_dict, min_idx, max_idx, col_name, step_size=1):
        return pd.DataFrame(data=data_dict.values(),
                            index=data_dict.keys(),
                            columns=[col_name]).reindex(list(range(min_idx, max_idx + 1, step_size))).interpolate()

    def plotly_summary(self, height=350, width=800):
        plot_df = (self.df[['give_recommendation_m']].reset_index().rename(
            columns={'age': 'Age'}
        )
        )
        plot_df['Suggested Giving [k / month]'] = (plot_df['give_recommendation_m'] * 1000 / 12).round(0)
        fig = px.line(plot_df, x='Age', y='Suggested Giving [k / month]')
        fig.update_layout(height=height, width=width, title='Give recommendation per age [k / month]')
        return fig

    def plotly_summary_cum(self, height=350, width=800):

        plot_df = (self.df[['give_recommendation_m']].cumsum().round(3).reset_index().rename(
            columns={'age': 'Age', 'give_recommendation_m': 'Cum. Suggested Giving [m / year]'}
        )
        )

        fig = px.line(plot_df, x='Age', y='Cum. Suggested Giving [m / year]')
        fig.update_layout(height=height, width=width, title='Cumulative give recommendation per age [m / year]')
        return fig


def get_A_ub(length: int, r: float = 1.1) -> np.ndarray:
    A_ub = np.zeros((length, length))
    for i in range(len(A_ub)):
        for j in range(len(A_ub)):
            if i >= j:
                A_ub[i, j] = r ** (i - j)
    return A_ub


def get_b_ub(disp: dict, r: float) -> list:
    b_ub = []
    i_min = min(disp.keys())
    for age in disp.keys():
        res_list = [disp[age_] * r ** (age - age_ + 1) for age_ in range(i_min, age + 1)]
        res = sum(res_list)
        b_ub.append(res)
    return b_ub


def get_optimization_variables(conf: Config):

    # Unpack
    disp = conf.df.disposable_salary.to_dict()
    leak_mult = conf.df.leak_multiplier.to_dict()
    r = conf.net_return_mult

    # Get vectors and matrices for optimization
    c = -1 * np.array(list(leak_mult.values()))
    A_ub = get_A_ub(length=len(disp), r=r)
    b_ub = get_b_ub(disp=disp, r=r)

    return c, A_ub, b_ub


def run_linear_optimization(conf: Config):
    c, A_ub, b_ub = get_optimization_variables(conf)
    result = linprog(c, A_ub, b_ub)
    tot_given = round(np.sum(result.x), 3)
    lives_saved = int(round(tot_given / conf.save_qa_life_cost_k))
    conf.lives_saved = lives_saved
    conf.sum_given_m = tot_given/1000
    conf.df['give_recommendation_m'] = np.array(result.x)/1000


st.title("""Explore how many lives you can save over your lifetime""")

ea_intro = ('https://www.youtube.com/watch?v=Diuv3XZQXyc')

st.write("This is a tool for exploring how many lives you can save over your own lifetime by giving to the most "
         "effective charities, and is inspired by the Effective Altruism movement, see: "
         "[Intro Video](%s)" % ea_intro)
st.write("More specifically, the purpose of the tool is to: ")
st.write("1) Hopefully get you inspired and motivated about saving more lives")
st.write("2) Explore how different assumptions impact *when* it is best to give to save most lives. "
         "Assumptions include salary at different age, return on the stock market, discount rate for waiting to give, "
         "and assumed future likelihood of *actually* giving. This might give rise to new "
         "ideas and perspectives on *when* it might be best to give to charity, and how to *ensure* it's done.")

with st.form("input_assumptions", clear_on_submit=False):

    save_qa_life_cost_k = st.slider('Cost of saving a life [k] at full quality (e.g. roughly $3000 - $4500 or '
                                    '27 - 41 k SEK)', min_value=1, max_value=200, value=35)

    givewell_url = ('https://www.givewell.org/charities/top-charities')
    st.caption("Cost of saving a life at full quality can be estimated from randomized controlled trials, "
               " see for example [GiveWell top charities](%s)" % givewell_url)

    current_age = st.slider('Current age', min_value=15, max_value=120, value=30)
    life_exp_years = st.slider('Life expectency', min_value=15, max_value=200, value=80)
    current_savings_k = st.number_input('Current savings [k]', min_value=0, max_value=1000000, value=0)
    return_rate_after_inflation_percent = st.slider('Stock market return rate after inflation [%]',
                                                    min_value=0.0, max_value=20.0, value=3.0, step=0.1)

    existential_risk_discount_rate_percent = st.slider('Discount rate for cost of existential risk '
                                                       'and global suffering [%]. ',
                                                       min_value=0.0, max_value=10.0, value=3.0, step=0.01)

    x_risk_derivation = ('https://forum.effectivealtruism.org/posts/3fmcNMrR8cktLnoYk/' +
                         'giving-now-vs-later-for-existential-risk-an-initial-approach')
    st.caption("Existential risk: Yearly discount rate for existential risk ≈ rate of extinction according to this "
               "[x-risk derivation](%s)" % x_risk_derivation)
    st.caption("Global suffering: The discount rate might be related to the growth rate of developing countries, "
               "suggesting it might be more expensive to save lives in the future.")

    month_salary_k_per_age = st.text_input('Month salary before tax [k] at different sample ages as a dictionary '
                                           '{age: salary}, they will be interpolated linearly',
                                           value='{30: 40, 40: 50, 64: 55, 66: 15}')

    month_req_cost_k_per_age = st.text_input('Required cost of living per month [k] per age as a dictionary '
                                             '{age: cost}, they will be interpolated linearly',
                                             value='{30: 18, 65: 20, 66: 15}')

    share_tax_per_k_salary = st.text_input('Enter share total tax at ranges that cover at least min and '
                                           'max salary [k] above and preferably some points in between as a dictionary'
                                           ', {salary: share_tax}, it will be interpolated linearly (can be found '
                                           ' in various salary-after-tax calculators online)',
                                           value='{10: 0.18, 20: 0.2, 30: 0.2, 40: 0.225, '
                                                 '50: 0.26, 60: 0.3, 100: 0.38}')

    leak_multiplier_per_age = st.text_input('Enter expected leaking factor (1 = no leaking) at different ages as a dictionary '
                                            'leaking money to other causes like borrowing to relatives or passing away '
                                            'without testament or with legal requirements on inheritence etc. ',
                                            value='{30: 0.95, 45: 0.9, 55: 0.80, 80: 0.5}')

    submit = st.form_submit_button('Run giving optimizer!')

    st.caption("""The tool uses linear optimization to find the presumed 'optimal' giving at each age of your life to 
                  maximize number of lives saved, but needs to be combined with other perspectives. 
                  For example, recurring giving can help us stay engaged in doing good and inspire 
                  others to give, even out donation flows to charities etc.""")
    st.caption("If you get error messages when running, it is likely due to invalid data in the input fields. "
               "You can always reload the browser to rerun with the default values, then change them step by step "
               "and check everything works.")
    st.caption("When the stock market return is higher than the discount rate, the tool will generally favour "
               "waiting to give, and conversely, when the discount rate is higher it will generally suggest giving "
               "as much as possible straight way, though this also depends on assumptions about the leaking factor.")

    code_git = ('https://github.com/simoncelinder/ea-giving-optimizer')
    st.caption("The code for this tool is available in git: [link](%s)" % code_git)


if submit:

    month_salary_k_per_age = eval(month_salary_k_per_age)
    share_tax_per_k_salary = eval(share_tax_per_k_salary)
    month_req_cost_k_per_age = eval(month_req_cost_k_per_age)
    leak_multiplier_per_age = eval(leak_multiplier_per_age)

    return_rate_after_inflation = return_rate_after_inflation_percent / 100
    existential_risk_discount_rate = existential_risk_discount_rate_percent / 100

    conf = Config(
        save_qa_life_cost_k=save_qa_life_cost_k,
        current_age=current_age,
        life_exp_years=life_exp_years,
        current_savings_k=current_savings_k,
        return_rate_after_inflation=return_rate_after_inflation,
        existential_risk_discount_rate=existential_risk_discount_rate,
        month_salary_k_per_age=month_salary_k_per_age,
        month_req_cost_k_per_age=month_req_cost_k_per_age,
        share_tax_per_k_salary=share_tax_per_k_salary,
        leak_multiplier_per_age=leak_multiplier_per_age
    )
    run_linear_optimization(conf)
    st.write(f"Lives saved: {conf.lives_saved}, Sum given: {conf.sum_given_m :.2f} [m] ")
    ffill_note = conf.get_ffill_note()
    if ffill_note is not None:
        st.caption(ffill_note)

    # Plotly graphs
    height, width = 300, 750
    st.plotly_chart(conf.plotly_summary(height=height, width=width))
    st.plotly_chart(conf.plotly_summary_cum(height=height, width=width))

    # Lives saved as person symbols
    st.write(f'Lives saved at full quality of life visualized as people')
    st.write('👤 ' * conf.lives_saved)
