from ea_giving_optimizer.app import Config, get_b_ub, run_linear_optimization
import pytest
import numpy as np


def get_dummy_conf(
        current_age=10,
        life_exp_years=15,
        current_savings_k=0,
        month_salary_k_per_age=None,
        month_req_cost_k_per_age=None,
        share_tax_per_k_salary=None,
        return_rate_after_inflation=0.0,
        existential_risk_discount_rate=0.00,
        leak_multiplier_per_age=None,
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
    )


def test_get_b_ub():
    assert get_b_ub({4: 1, 5: 1, 6: 1}, r=1)[-1] == 3
    assert get_b_ub({4: 1, 5: 2.11, 6: 3}, r=1)[-1] == 1 + 2.11 + 3
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[0] == 1.11 * 2 ** 1
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[1] == 1.11 * 2 ** 2 + 2 * 2 ** 1
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[2] == 1.11 * 2 ** 3 + 2 * 2 ** 2 + 1 * 2 ** 1


def test_optimization_general():

    # When positive interest and no cost of x-risk, should recommend giving everything last
    conf = get_dummy_conf(return_rate_after_inflation=0.01)
    run_linear_optimization(conf)
    assert conf.df.iloc[-1]['give_recommendation_m'].round(1) == conf.df['give_recommendation_m'].sum().round(1)

    # When x-risk > interest, should recommend giving everything immediately per age
    conf = get_dummy_conf(existential_risk_discount_rate=0.02, return_rate_after_inflation=0.01)
    run_linear_optimization(conf)
    assert (conf.df['give_recommendation_m'].round(2) ==
            ((conf.df['disposable_salary']**conf.net_return_mult)/1000).round(2)).all()


def test_optimization_sum():

    # Tests that total given sum becomes consistent for random disposable incomes
    # and costs but with no interest or discount rates
    # (From manual testing, the small diff can have different sign from run to run,
    # indicating it would not be a systematic bias)

    error_decimal_tolerance = 0.02
    months_per_year = 12
    current_savings_k = np.random.uniform(low=3, high=10)

    d1 = np.random.uniform(low=3, high=10)
    d2 = np.random.uniform(low=3, high=10)
    d3 = np.random.uniform(low=3, high=10)
    d4 = np.random.uniform(low=3, high=10)
    d5 = np.random.uniform(low=3, high=10)
    d6 = np.random.uniform(low=3, high=10)

    c1 = np.random.uniform(low=1, high=2)
    c2 = np.random.uniform(low=1, high=2)
    c3 = np.random.uniform(low=1, high=2)
    c4 = np.random.uniform(low=1, high=2)
    c5 = np.random.uniform(low=1, high=2)
    c6 = np.random.uniform(low=1, high=2)

    conf = get_dummy_conf(
        month_salary_k_per_age={
            10: d1,
            11: d2,
            12: d3,
            13: d4,
            14: d5,
            15: d6,
        },
        month_req_cost_k_per_age={
            10: c1,
            11: c2,
            12: c3,
            13: c4,
            14: c5,
            15: c6,
        },
    )

    run_linear_optimization(conf)

    expected = months_per_year / 1000 * (
        (d1 - c1) +
        (d2 - c2) +
        (d3 - c3) +
        (d4 - c4) +
        (d5 - c5) +
        (d6 - c6) +
        current_savings_k / months_per_year  # No *12 on initial savings
    )

    is_success = conf.sum_given_m == pytest.approx(expected, error_decimal_tolerance)
    print(expected, conf.sum_given_m)

    assert is_success, (f"Too big discrepancy between expected optimization result and actual, "
              f"expected = {round(expected, 3)}, actual = {conf.sum_given_m}")
