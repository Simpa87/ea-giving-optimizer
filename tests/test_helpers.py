from ea_giving_optimizer.helpers import (
    get_b_ub,
    run_linear_optimization,
    create_dummy_conf
)
import pytest
import numpy as np


def test_get_b_ub():
    assert get_b_ub({4: 1, 5: 1, 6: 1}, r=1)[-1] == 3
    assert get_b_ub({4: 1, 5: 2.11, 6: 3}, r=1)[-1] == 1 + 2.11 + 3
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[0] == 1.11 * 2 ** 1
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[1] == 1.11 * 2 ** 2 + 2 * 2 ** 1
    assert get_b_ub({4: 1.11, 5: 2, 6: 1}, r=2)[2] == 1.11 * 2 ** 3 + 2 * 2 ** 2 + 1 * 2 ** 1


def test_optimization_general():

    # When positive interest and no cost of x-risk, should recommend giving everything last
    conf = create_dummy_conf(return_rate_after_inflation=0.01)
    run_linear_optimization(conf)
    assert conf.df.iloc[-1]['give_recommendation_m'].round(1) == conf.df['give_recommendation_m'].sum().round(1)

    # When x-risk > interest, should recommend giving everything immediately per age
    conf = create_dummy_conf(existential_risk_discount_rate=0.02, return_rate_after_inflation=0.01)
    run_linear_optimization(conf)
    assert (conf.df['give_recommendation_m'].round(2) ==
            ((conf.df['disposable_for_giving']**conf.net_return_mult)/1000).round(2)).all()


def test_optimization_sum():

    # Tests that total given sum becomes consistent for random disposable incomes
    # and costs but with no interest or discount rates
    # (From manual testing, the small diff can have different sign from run to run,
    # indicating it would not be a systematic bias)

    error_decimal_tolerance = 0.08
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

    conf = create_dummy_conf(
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

    assert is_success, (
        f"Too big discrepancy between expected optimization result and actual, "
        f"expected = {round(expected, 3)}, actual = {conf.sum_given_m}"
    )


def test_optimization_sum_simple_implementation_factor():

    # Testing same multiplier gets distributed across years
    error_decimal_tolerance = 0.025
    months_per_year = 12
    impl_factor = np.random.uniform(low=0, high=1)

    # Salary defaults to 10 k and costs to 5 k for each year
    net_savings_per_month_k = 5
    years_in_period = 6
    net_savings_per_year_k = net_savings_per_month_k * months_per_year
    net_savings_tot_k = net_savings_per_year_k * years_in_period
    expected = net_savings_tot_k / 1000 * impl_factor

    conf = create_dummy_conf(
        implementation_factor_per_age={
            10: impl_factor,
            15: impl_factor,
        },
    )

    run_linear_optimization(conf)
    is_success = conf.sum_given_m == pytest.approx(expected, error_decimal_tolerance)

    assert is_success, (
        f"Too big discrepancy between expected optimization result and actual, "
        f"expected = {round(expected, 3)}, actual = {conf.sum_given_m}"
    )


def test_bfill_conf():
    conf = create_dummy_conf(
        current_age=8,
        month_salary_k_per_age={10: np.random.uniform(low=8, high=10), 15: 10},
        month_req_cost_k_per_age={10: np.random.uniform(low=4, high=5), 15: 5}
    )
    df = conf.df

    # Backfill first missing age
    assert df.iloc[0]['salary_k'] == df.iloc[1]['salary_k']
    assert df.iloc[0]['req_cost_k_year'] == df.iloc[1]['req_cost_k_year']


def test_ffill_conf():
    conf = create_dummy_conf(
        life_exp_years=16,
        month_salary_k_per_age={10: 10, 15: np.random.uniform(low=10, high=12)},
        month_req_cost_k_per_age={10: 5, 15: np.random.uniform(low=5, high=7)}
    )
    df = conf.df

    # Ffill last missing age
    assert df.iloc[-1]['salary_k'] == df.iloc[-2]['salary_k']
    assert df.iloc[-1]['req_cost_k_year'] == df.iloc[-2]['req_cost_k_year']


def test_cut_at_age():
    conf = create_dummy_conf(
        current_age=12,
        month_salary_k_per_age={10: 10, 15: 15},
        month_req_cost_k_per_age={10: 5, 15: 10}
    )
    df = conf.df

    # Check interpolation and filling made right remaining values
    assert (df.salary_k.values == [12, 13, 14, 15]).all()
    assert (df.req_cost_k_year == [7*12, 8*12, 9*12, 10*12]).all()


def test_current_savings():
    savings_k = np.random.normal(10, 20)
    conf_savings = create_dummy_conf(
        current_age=12,
        month_salary_k_per_age={10: 10, 15: 15},
        month_req_cost_k_per_age={10: 5, 15: 10},
        current_savings_k=savings_k
    )
    df_savings = conf_savings.df

    conf = create_dummy_conf(
        current_age=12,
        month_salary_k_per_age={10: 10, 15: 15},
        month_req_cost_k_per_age={10: 5, 15: 10},
        current_savings_k=0
    )
    df = conf.df

    assert round(df.disposable_for_giving.sum() + savings_k, 3) == round(df_savings.disposable_for_giving.sum(), 3)
    assert round(df.disposable_for_giving.iloc[0] + savings_k, 3) == round(df_savings.disposable_for_giving.iloc[0], 3)


def test_pretax_giving():

    """
    (salary_pretax - disposable_for_giving) * (1 - share_tax) = req_cost
    <=> (salary_pretax - disposable_for_giving) = req_cost / (1 - share_tax)
    <=> disposable_for_giving = salary_pretax - req_cost / (1 - share_tax)
    """
    share_tax = 0.2
    # Constant for simplicity
    conf = create_dummy_conf(
        is_giving_pretax=True,
        month_salary_k_per_age={10: 10, 15: 10},
        month_req_cost_k_per_age={10: 5, 15: 5},
        share_tax_per_k_salary={0: share_tax, 20: share_tax},
    )
    df = conf.df

    assert (
        (
                df['disposable_for_giving'] == (df['salary_k_year'] - df['req_cost_k_year'] / (1 - df['share_tax']))
                .round(0)
        ).all()
    )

    run_linear_optimization(conf)
    error_decimal_tolerance = 0.0001
    expected = df['disposable_for_giving'].sum()
    is_success = conf.sum_given_m * 1000 == pytest.approx(expected, error_decimal_tolerance)

    assert is_success, (
        f"Too big discrepancy between expected optimization result and actual, "
        f"expected = {round(expected, 3)}, actual = {conf.sum_given_m}"
    )

    """ 
    Ratio difference test:
    Not is_giving_pretax: disposable_for_giving = salary_pretax * (1 - share_tax) - req_cost
    is_giving_pretax: disposable_for_giving = salary_pretax - req_cost / (1 - share_tax)
    ratio = (salary_pretax - req_cost / (1 - share_tax)) / (salary_pretax * (1 - share_tax) - req_cost) 
    E.g. with values (10 - 5 / 0.8) / ((1 - 0.2) / (10 * 0.8 - 5) = 1.25
    Making ratio = 1.25 = 1 / (1 - share_tax)
    
    Hardcoded reality check for more intuition:
    Not pretax: 10 * 0.8 - disposable = 5 => disposable = 3
    Pretax: (10 - disposable) * 0.8 = 5 => 3.75
    Ratio: 3.75 / 3 = 1.25
    """

    conf_post_tax = create_dummy_conf(
        is_giving_pretax=False,
        month_salary_k_per_age={10: 10, 15: 10},
        month_req_cost_k_per_age={10: 5, 15: 5},
        share_tax_per_k_salary={0: share_tax, 20: share_tax},
    )
    run_linear_optimization(conf_post_tax)
    assert conf_post_tax.sum_given_m / (1 - share_tax) == pytest.approx(conf.sum_given_m, 0.005)
