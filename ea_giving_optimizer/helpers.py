import pandas as pd
import numpy as np
import optuna



class Config:

    def __init__(self,
                 # Just example data!
                 month_salary_k_per_age={30: 53, 40: 65, 45: 55, 65: 50, 66: 0},  # 0 at retire age
                 month_req_cost_k_per_age={30: 20, 65: 20, 66: 20},
                 share_tax_per_k_salary={10: (1 - 8.2 / 10), 20: (1 - 16 / 20), 30: (1 - 24 / 30), 40: (1 - 31 / 40),
                                         50: (1 - 37 / 50), 60: (1 - 42 / 60), 80000: (1 - 52 / 80)},
                 current_age=30,
                 current_savings_k=0,
                 life_exp_years=80,
                 return_after_inflation=1.04,
                 ):
        self.life_exp_years = life_exp_years
        self.return_after_inflation = return_after_inflation

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
        salary_per_age_df = salary_per_age_df.round(
            1)  # For join

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

        # Only include cumulation and compounding from current age
        df = df.loc[df.index >= current_age]

        df['years'] = np.arange(len(df))
        df['compound_interest'] = self.return_after_inflation ** df['years']
        df['salary_k_year'] = df['salary_k'] * 12
        df['salary_k_year_after_tax'] = (df['salary_k_year'] * (1 - df['share_tax'])).round(0)
        df['disposable_salary'] = (df['salary_k_year_after_tax'] - df['req_cost_k_year']).round(0)
        df['disposable_salary'] = df['disposable_salary'].ffill()
        df['cum_disposable_k'] = df['disposable_salary'].cumsum()

        # Only add savings after cumsum
        df['cum_disposable_k'] += current_savings_k

        # Apply compound interest (also to current_savings)
        df['cum_disp_inc_return_k'] = df['cum_disposable_k'] * df['compound_interest'].round(0)
        df['cum_disp_inc_return_m'] = (df['cum_disp_inc_return_k'] / 1000).round(2)

        # For reality check
        df['disposable_salary_w_interest'] = df['disposable_salary'] * df['compound_interest'].round(0)

        df = df.fillna(0).set_index('age')
        self.df = df

    def interpolate_df_from_dict(self, data_dict, min_idx, max_idx, col_name, step_size=1):
        return pd.DataFrame(data=data_dict.values(),
                            index=data_dict.keys(),
                            columns=[col_name]).reindex(list(range(min_idx, max_idx + 1, step_size))).interpolate()


def remains(disp, give_share, i, r) -> float:
    i -= 1
    if i >= min(disp.keys()):
        return (1 - give_share[i]) * (disp[i] * r +
                                      remains(disp, give_share, i, r) * r  # One step interest
                                      if give_share[i] != 1 else 0  # Stop backward search if gave all (validated works)
                                      )
    else:
        return 0


def tot_give(disp, give_share, r):
    i_min = min(give_share.keys())
    i_max = max(give_share.keys())
    return sum([give_share[i] * (disp[i] + remains(disp, give_share, i_max, r)) for i in range(i_min, i_max + 1)]) * r


def get_baseline_giving(c: Config) -> dict:

    # Give everything last with interest as baseline to enqueue to run first
    baseline_dict = {}
    for i in list(c.df.index):
        if i != max(c.df.index):
            baseline_dict[i] = 0
        else:
            baseline_dict[i] = 1
    return baseline_dict


def best_giving_optuna(
        c: Config,
        enqueue_baseline: bool = True,
        n_trials: int = 50) -> dict:

    # Inline to pass disp, maybe factor out class to pass the nicer way
    disp = c.df['disposable_salary'].to_dict()  # TODO + initial savings

    def giving_objective_optuna(trial):
        give_share_dict = {}
        for i in list(disp.keys()):
            give_share_dict[i] = trial.suggest_float(i, 0, 1)
        return tot_give(disp, give_share_dict, r=c.return_after_inflation)

    study = optuna.create_study(direction='maximize')
    if enqueue_baseline:
        baseline_dict = get_baseline_giving(c)
        study.enqueue_trial(baseline_dict)
    study.optimize(giving_objective_optuna, n_trials=n_trials)
    return study.best_params

