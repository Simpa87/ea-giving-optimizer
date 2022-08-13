import numpy as np
import pandas as pd
from plotly import express as px
from scipy.optimize import linprog


class Config:

    def __init__(self,
                 # Just example data!

                 # General assumptions
                 current_age: int,
                 current_savings_k: float,
                 life_exp_years: int,
                 save_qa_life_cost_k: float,
                 is_giving_pretax: bool,

                 # Per age
                 month_salary_k_per_age: dict,
                 month_req_cost_k_per_age: dict,

                 # Marginal taxation
                 share_tax_per_k_salary: dict,

                 # Return on savings e.g. stock market rate
                 return_rate_after_inflation: float,

                 # Cost of exponential risks compounding
                 existential_risk_discount_rate: float,

                 # Leaking money to other causes
                 leak_multiplier_per_age: dict,
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
        self.is_giving_pretax = is_giving_pretax
        assert 0.01 <= self.net_return_mult <= 2  # Return multiplier can be < 1 after existential risk

        # Save for metadata e.g. prints on ffill
        self.leak_multiplier_per_age = leak_multiplier_per_age
        self.month_salary_k_per_age = month_salary_k_per_age
        self.month_req_cost_k_per_age = month_req_cost_k_per_age

        salary_per_age_df = self.interpolate_df_from_dict(
            month_salary_k_per_age,
            min_idx=min(month_salary_k_per_age.keys()),
            max_idx=max(month_salary_k_per_age.keys()),
            col_name='salary_k'
        )

        cost_per_age_df = self.interpolate_df_from_dict(
                month_req_cost_k_per_age,
                min_idx=min(month_req_cost_k_per_age.keys()),
                max_idx=max(month_req_cost_k_per_age.keys()),
                col_name='req_cost'
            )

        salary_per_age_df.index.name = 'age'

        # Round for integer join
        salary_per_age_df = salary_per_age_df.round(0)

        self.tax_per_salary_df = self.interpolate_df_from_dict(
            share_tax_per_k_salary,
            min_idx=int(min(share_tax_per_k_salary.keys())),
            max_idx=int(max(share_tax_per_k_salary.keys())),
            col_name='share_tax',
            step_size=1
        )

        self.tax_per_salary_df.index.name = 'salary_k'
        df = pd.merge(
            left=salary_per_age_df.reset_index(),
            right=self.tax_per_salary_df.reset_index(),
            on='salary_k',
            how='left'
        )

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


        # Need to ffill and bfill after the join, which needs to initially be before cutting at "age"
        # to capture start and stop values that might be outside bounds
        df = self.ffill_bfill_cols(df)

        # Reindex if current_age or death is outside bounds for other values
        df = (
            df
            .set_index('age')
            .reindex(list(range(current_age, life_exp_years + 1)))
            .reset_index()
        )

        # Once again fill cols if age or death was outside bounds
        df = self.ffill_bfill_cols(df)

        # Can now filter df to only include values from current age
        df = df.loc[df['age'] >= current_age]

        df['years'] = np.arange(len(df))
        df['compound_interest'] = self.net_return_mult ** df['years']  # After infl and exist risk
        df['salary_k_year'] = df['salary_k'] * 12

        df = self.calc_disposable_for_giving(df, is_giving_pretax)

        # Add current savings which are assumed already tax
        df.loc[df['age'] == current_age, 'disposable_for_giving'] += current_savings_k

        df['disposable_for_giving'] = df['disposable_for_giving'].ffill()

        df = df.set_index('age')
        self.df = df

        # Placeholders for result
        self.sum_given_m = None
        self.lives_saved = None

    @staticmethod
    def calc_disposable_for_giving(df, is_giving_pretax):
        df = df.copy()
        if is_giving_pretax:
            df['disposable_for_giving'] = (df['salary_k_year'] - df['req_cost_k_year'] / (1 - df['share_tax'])).round(0)
        else:
            df['salary_k_year_after_tax'] = (df['salary_k_year'] * (1 - df['share_tax'])).round(0)
            df['disposable_for_giving'] = (df['salary_k_year_after_tax'] - df['req_cost_k_year']).round(0)
        return df

    @staticmethod
    def ffill_bfill_cols(df):
        df = df.copy()
        df['salary_k'] = df['salary_k'].ffill().bfill()
        df['req_cost_k_year'] = df['req_cost_k_year'].ffill().bfill()
        df['leak_multiplier'] = df['leak_multiplier'].ffill().bfill()
        return df

    def interpolate_df_from_dict(self, data_dict, min_idx, max_idx, col_name, step_size=1):
        return (
            pd.DataFrame(
                data=data_dict.values(),
                index=data_dict.keys(),
                columns=[col_name]
            )
            .reindex(list(range(min_idx, max_idx + 1, step_size)))
            .interpolate(limit_area='inside')
        )

    def plotly_summary(self, height=350, width=800):
        plot_df = (
            self.df[['give_recommendation_k']].round(3).reset_index().rename(
                columns={'age': 'Age', 'give_recommendation_k': 'Suggested Giving [k USD]'}
            )
        )
        fig = px.line(plot_df, x='Age', y='Suggested Giving [k USD]')
        fig.update_layout(height=height, width=width, title='Give recommendation per age [thousand USD]')
        return fig

    def plotly_summary_cum(self, height=350, width=800):
        plot_df = (
            self.df[['give_recommendation_m']].cumsum().round(3).reset_index().rename(
                columns={'age': 'Age', 'give_recommendation_m': 'Cum. Suggested Giving [m USD]'}
            )
        )
        fig = px.line(plot_df, x='Age', y='Cum. Suggested Giving [m USD]')
        fig.update_layout(height=height, width=width, title='Cumulative give recommendation per age [million USD]')
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
    disp = conf.df.disposable_for_giving.to_dict()
    leak_mult = conf.df.leak_multiplier.to_dict()
    r = conf.net_return_mult

    # Get vectors and matrices for optimization
    c_leak = -1 * np.array(list(leak_mult.values()))
    A_ub = get_A_ub(length=len(disp), r=r)
    b_ub = get_b_ub(disp=disp, r=r)

    return c_leak, A_ub, b_ub


def run_linear_optimization(conf: Config):
    c_leak, A_ub, b_ub = get_optimization_variables(conf)
    result_obj = linprog(c_leak, A_ub, b_ub)
    result = result_obj.x
    leaking_adj_result = result * c_leak * (-1)
    tot_given = round(np.sum(leaking_adj_result), 3)
    lives_saved = int(round(tot_given / conf.save_qa_life_cost_k))
    conf.lives_saved = lives_saved
    conf.sum_given_m = tot_given/1000
    conf.df['give_recommendation_m'] = np.array(leaking_adj_result)/1000
    conf.df['give_recommendation_k'] = np.array(leaking_adj_result)


def create_dummy_conf(
        current_age=10,
        life_exp_years=15,
        current_savings_k=0,
        save_qa_life_cost_k=3500,
        month_salary_k_per_age=None,
        month_req_cost_k_per_age=None,
        share_tax_per_k_salary=None,
        return_rate_after_inflation=0.0,
        existential_risk_discount_rate=0.00,
        leak_multiplier_per_age=None,
        is_giving_pretax=False,
):

    # Avoid mutable default args
    if month_salary_k_per_age is None:
        month_salary_k_per_age = {10: 10, 15: 10}
    if month_req_cost_k_per_age is None:
        month_req_cost_k_per_age = {10: 5, 15: 5}
    if share_tax_per_k_salary is None:
        share_tax_per_k_salary = {0: 0, 1000: 0}
    if leak_multiplier_per_age is None:
        leak_multiplier_per_age = {10: 1, 15: 1}

    return Config(
        current_age=current_age,
        life_exp_years=life_exp_years,
        current_savings_k=current_savings_k,
        month_salary_k_per_age=month_salary_k_per_age,
        month_req_cost_k_per_age=month_req_cost_k_per_age,
        share_tax_per_k_salary=share_tax_per_k_salary,
        return_rate_after_inflation=return_rate_after_inflation,
        existential_risk_discount_rate=existential_risk_discount_rate,
        leak_multiplier_per_age=leak_multiplier_per_age,
        is_giving_pretax=is_giving_pretax,
        save_qa_life_cost_k=save_qa_life_cost_k,
    )


def dict_values_to_thousands(original_dict: dict):
    new_dict = original_dict.copy()
    new_dict.update((k, v / 1000) for k, v in new_dict.items())
    return new_dict


def dict_keys_to_thousands(original_dict: dict):
    new_dict = original_dict.copy()
    for k in list(new_dict.keys()):
        new_dict[k/1000] = new_dict.pop(k)
    return new_dict


def check_valid_keys(current_age, month_salary_k_per_age, month_req_cost_k_per_age, implementation_factor_per_age):
    min_key = min(
        list(month_salary_k_per_age.keys()) +
        list(month_req_cost_k_per_age.keys())
    )
    if implementation_factor_per_age is not None:
        min_key = min(min_key, min(implementation_factor_per_age.keys()))
    is_keys_ok = current_age >= min_key
    return is_keys_ok