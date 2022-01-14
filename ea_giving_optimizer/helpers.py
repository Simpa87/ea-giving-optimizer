import pandas as pd
import numpy as np
from scipy.optimize import linprog
import matplotlib.pyplot as plt


class Config:

    def __init__(self,
                 # Just example data!

                 # General assumptions
                 current_age=30,
                 current_savings_k=0,  # Currently not used
                 life_exp_years=80,
                 save_qa_life_cost_k=35,

                 # Per age
                 month_salary_k_per_age={30: 53, 40: 65, 45: 55, 65: 50, 66: 0},  # 0 at retire age
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
        assert all((0 <= v <= 1) for v in leak_multiplier_per_age.values())
        assert life_exp_years > current_age
        assert -0.1 <= return_rate_after_inflation <= 0.3
        assert 0 <= existential_risk_discount_rate <= 0.99

        if leak_multiplier_per_age is not None:
            assert current_age == min(leak_multiplier_per_age.keys())
            assert life_exp_years == max(leak_multiplier_per_age.keys())

        self.life_exp_years = life_exp_years
        self.save_qa_life_cost_k = save_qa_life_cost_k
        self.net_return_mult = 1 + return_rate_after_inflation - existential_risk_discount_rate
        assert 0.01 <= self.net_return_mult <= 2  # Return multiplier can be < 1 after existential risk

        salary_per_age_df = self.interpolate_df_from_dict(
            month_salary_k_per_age,
            min_idx=0,
            max_idx=life_exp_years,
            col_name='salary_k'
        ).fillna(0)  # Initial and last years assume 0?

        cost_per_age_df = self.interpolate_df_from_dict(
            month_req_cost_k_per_age,
            min_idx=0,
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
        df = df.loc[df.index >= current_age]

        df['years'] = np.arange(len(df))
        df['compound_interest'] = self.net_return_mult ** df['years']  # After infl and exist risk
        df['salary_k_year'] = df['salary_k'] * 12
        df['salary_k_year_after_tax'] = (df['salary_k_year'] * (1 - df['share_tax'])).round(0)
        df['disposable_salary'] = (df['salary_k_year_after_tax'] - df['req_cost_k_year']).round(0)
        df['disposable_salary'] = df['disposable_salary'].ffill()

        df = df.fillna(0).set_index('age')
        self.df = df

        # Placeholders for result
        self.sum_given_m = None
        self.lives_saved = None


    def interpolate_df_from_dict(self, data_dict, min_idx, max_idx, col_name, step_size=1):
        return pd.DataFrame(data=data_dict.values(),
                            index=data_dict.keys(),
                            columns=[col_name]).reindex(list(range(min_idx, max_idx + 1, step_size))).interpolate()

    def plot_summary(self, figsize=(20, 4)):
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        self.df[['give_recommendation_m']].plot(title='Give recommendation [m]', ax=axes[0])
        self.df[['give_recommendation_m']].cumsum().plot(title='Cumulative give recommendation [m]', ax=axes[1])
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


def run_linear_optimization(conf: Config, figsize=(20, 5)):
    c, A_ub, b_ub = get_optimization_variables(conf)
    result = linprog(c, A_ub, b_ub)
    tot_given = round(np.sum(result.x), 3)
    lives_saved = int(round(tot_given / conf.save_qa_life_cost_k))
    conf.lives_saved = lives_saved
    conf.sum_given_m = round(tot_given/1000, 1)
    conf.df['give_recommendation_m'] = np.array(result.x)/1000
    conf.plot_summary(figsize=figsize)
