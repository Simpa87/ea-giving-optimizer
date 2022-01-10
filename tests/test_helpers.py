from ea_giving_optimizer.helpers import get_b_ub, Config, run_linear_optimization


def get_dummy_conf(
        current_age=10,
        life_exp_years=15,
        month_salary_k_per_age={10: 10, 15: 10},
        month_req_cost_k_per_age={10: 5, 15: 5},
        share_tax_per_k_salary={10: 0},
        return_rate_after_inflation=0.0,
        existential_risk_discount_rate=0.00,
        leak_multiplier_per_age={10: 1, 15: 1},
):
    return Config(
        current_age=current_age,
        life_exp_years=life_exp_years,
        month_salary_k_per_age=month_salary_k_per_age,
        month_req_cost_k_per_age=month_req_cost_k_per_age,
        share_tax_per_k_salary=share_tax_per_k_salary,
        return_rate_after_inflation=return_rate_after_inflation,
        existential_risk_discount_rate=existential_risk_discount_rate,
        leak_multiplier_per_age=leak_multiplier_per_age,
    )


def test_get_b_ub():
    assert get_b_ub({4: 1, 5: 1, 6: 1}, r=1)[-1] == 3
    assert get_b_ub({4: 1, 5: 2.11, 6: 3}, r=1)[-1] == 1 + 2.11 + 3
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[0] == 1.11 * 2 ** 1
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[1] == 1.11 * 2 ** 2 + 2 * 2 ** 1
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[2] == 1.11 * 2 ** 3 + 2 * 2 ** 2 + 1 * 2 ** 1


def test_optimization():

    # When positive interest and no cost of x-risk, should recommend giving everything last
    conf = get_dummy_conf(return_rate_after_inflation=0.01)
    run_linear_optimization(conf)
    assert conf.df.iloc[-1]['give_recommendation_m'].round(1) == conf.df['give_recommendation_m'].sum().round(1)

    # When x-risk > interest, should recommend giving everything immediately per age
    conf = get_dummy_conf(existential_risk_discount_rate=0.02, return_rate_after_inflation=0.01)
    run_linear_optimization(conf)
    assert (conf.df['give_recommendation_m'].round(2) ==
            ((conf.df['disposable_salary']**conf.net_return_mult)/1000).round(2)).all()
