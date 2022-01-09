import pandas as pd
import numpy as np
import optuna
from scipy.optimize import linprog


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
                 existential_risk_discount_rate=0.08,

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

    def interpolate_df_from_dict(self, data_dict, min_idx, max_idx, col_name, step_size=1):
        return pd.DataFrame(data=data_dict.values(),
                            index=data_dict.keys(),
                            columns=[col_name]).reindex(list(range(min_idx, max_idx + 1, step_size))).interpolate()

    def print_lives_saved(self):
        print(round(self.df['cum_net_give'].iloc[-1] / self.save_qa_life_cost_k), "lives saved")


def remains(
        disp: dict,
        give_share: dict,
        i: int,
        r: float,
) -> float:
    if i >= min(disp.keys()):
        tot_remains = ((1 - give_share[i])
                       * (disp[i] * r + remains(disp, give_share, i - 1, r) * r if give_share[i] != 1 else 0)
                       )
        return tot_remains

    else:
        return 0


def tot_give(
        disp: dict,
        give_share: dict,
        r: float,
        leak_mult: dict = None,
) -> float:

    i_min = min(give_share.keys())
    i_max = max(give_share.keys())
    return (
            sum([give_share[i] * (leak_mult[i] if leak_mult is not None else 1)
                 * (disp[i] + remains(disp, give_share, i - 1, r))
                 for i in range(i_min, i_max + 1)])
            * r)


def cum_res_dicts(
        c: Config,
        give_share_rec: dict,
) -> tuple:

    # Get absolute number result by applying recursively
    nom_give_dict = {}
    tot_leak_dict = {}
    net_give_dict = {}

    for i in give_share_rec.keys():

        # Prep variables
        give_share_i = pd.Series(give_share_rec).loc[min(give_share_rec.keys()):i].to_dict()
        disp = c.df['disposable_salary'].loc[min(give_share_rec.keys()):i].to_dict()
        leak_mult = c.df['leak_multiplier'].loc[min(give_share_rec.keys()):i].to_dict()

        # Without leaking
        nom_give_dict[i] = tot_give(disp, give_share_i, r=c.net_return_mult, leak_mult=None)

        # After leaking
        net_give_dict[i] = tot_give(disp, give_share_i, r=c.net_return_mult, leak_mult=leak_mult)

        # Separate out leaking for visualizations
        tot_leak_dict[i] = nom_give_dict[i] - net_give_dict[i]

    return nom_give_dict, net_give_dict, tot_leak_dict


def apply_cum_metrics(
        c: Config,
        give_share_rec: dict,
) -> Config:

    nom_give_dict, net_give_dict, tot_leak_dict = cum_res_dicts(c, give_share_rec)

    c.df['cum_nom_give'] = pd.Series(nom_give_dict)
    c.df['cum_tot_leak'] = pd.Series(tot_leak_dict)
    c.df['cum_net_give'] = pd.Series(net_give_dict)

    return c


def give_all_last(c: Config) -> dict:

    # Give everything last with interest as baseline to enqueue to run first
    give_last_dict = {}
    for i in list(c.df.index):
        if i != max(c.df.index):
            give_last_dict[i] = 0
        else:
            give_last_dict[i] = 1
    return give_last_dict


def give_all_always(c: Config) -> dict:

    # Give everything last with interest as baseline to enqueue to run first
    give_always_dict = {}
    for i in list(c.df.index):
        give_always_dict[i] = 1

    return give_always_dict


def give_half_always(c: Config) -> dict:

    # Give 50% all the time except give everything last
    give_half_dict = {}
    for i in list(c.df.index):
        if i != max(c.df.index):
            give_half_dict[i] = 0.5
        else:
            give_half_dict[i] = 1

    return give_half_dict


def give_linear_increase(c: Config) -> dict:

    # Give 50% all the time except give everything last
    linear_increase_dict = {}
    i_max = max(c.df.index)
    i_min = min(c.df.index)
    for i in list(c.df.index):
        linear_increase_dict[i] = (i - i_min) / (i_max - i_min)

    return linear_increase_dict


def best_giving_optuna(
        c: Config,
        enqueue_baseline: bool = True,
        n_trials: int = 50) -> dict:

    # Inline to pass disp, maybe factor out class to pass the nicer way
    disp = c.df['disposable_salary'].to_dict()  # TODO initial savings
    leak_mult = c.df['leak_multiplier'].to_dict() if not (c.df['leak_multiplier'] == 1).all() else None

    def giving_objective_optuna(trial):
        give_share_dict = {}
        for i in list(disp.keys()):
            give_share_dict[i] = trial.suggest_float(i, 0, 1)
        return tot_give(disp, give_share_dict, r=c.net_return_mult, leak_mult=leak_mult)

    study = optuna.create_study(direction='maximize')
    if enqueue_baseline:
        give_last_dict = give_all_last(c)
        study.enqueue_trial(give_last_dict)
        give_all_dict = give_all_always(c)
        study.enqueue_trial(give_all_dict)
        give_half_dict = give_half_always(c)
        study.enqueue_trial(give_half_dict)
        linear_increase_dict = give_linear_increase(c)
        study.enqueue_trial(linear_increase_dict)

    study.optimize(giving_objective_optuna, n_trials=n_trials)
    return study.best_params


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
    i_max = max(disp.keys())
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
    print(f"\nQuality adjusted lives saved: {lives_saved}")
    print(f"\nSum given {tot_give}")
    print("\nRecommended tot given per age:", dict(zip(list(conf.df.index), [round(i, 2) for i in result.x])))
    return result

