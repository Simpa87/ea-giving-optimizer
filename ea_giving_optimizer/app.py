import streamlit as st
from ea_giving_optimizer.helpers import Config, run_linear_optimization

# TODO:
#  - Plot works but choose nicer format, maybe plotly for interactive and dark background?
#  - Consider if refactor config into just a GivingOptimizer class that itself calls optimizer method
#  - Add so that initial savings can be used
#  - Containerize with docker-compose?
#  - Maybe rates * 100 for % so easier to slide? Or just more decimalc on the slider itself


st.title("""Effective Altruism Giving Optimizer""")
with st.form("input_assumptions", clear_on_submit=False):

    save_qa_life_cost_k = st.slider('Cost of saving a life [k] at full quality (e.g. roughly 3.5 k Euro or '
                                    '35 k SEK)', min_value=1, max_value=200, value=35)
    current_age = st.slider('Current age', min_value=15, max_value=120, value=30)
    life_exp_years = st.slider('Life expectency', min_value=15, max_value=200, value=80)
    return_rate_after_inflation_percent = st.slider('Return rate after inflation [%]',
                                            min_value=0.0, max_value=20.0, value=5.0, step=0.1)
    existential_risk_discount_rate_percent = st.slider('Discount rate for cost of existential risk '
                                                       'and global suffering [%]',
                                                       min_value=0.0, max_value=10.0, value=0.2, step=0.01)

    month_salary_k_per_age = st.text_input('Month salary before tax [k] at different sample ages as a dictionary '
                                           '{age: salary}, they will be interpolated linearly',
                                           value='{30: 40, 40: 50, 64: 55, 65: 10}')

    month_req_cost_k_per_age = st.text_input('Required cost of living per month [k] per age as a dictionary '
                                           '{age: cost}, they will be interpolated linearly - '
                                           'example with retirement at 65: ',
                                           value='{30: 18, 65: 20, 66: 17}')

    share_tax_per_k_salary = st.text_input('Enter share total tax at ranges that cover at least min and '
                                           'max salary [k] above and preferably some points in between as a dictionary'
                                           ', {salary: share_tax}, it will be interpolated linearly (can be found '
                                           ' in various salary-after-tax calculators online)',
                                           value='{10: 0.18, 20: 0.2, 30: 0.2, 40: 0.225, 50: 0.26, 60: 0.3}')

    leak_multiplier_per_age = st.text_input('Enter expected leaking factor (1 = no leaking) at different ages as a dictionary '
                                            'leaking money to other causes like borrowing to relatives or passing away '
                                            'without testament or with legal requirements on inheritence etc. ',
                                            value='{30: 0.95, 45: 0.9, 55: 0.80, 80: 0.5}')

    submit = st.form_submit_button('Run giving optimizer!')

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
        return_rate_after_inflation=return_rate_after_inflation,
        existential_risk_discount_rate=existential_risk_discount_rate,
        month_salary_k_per_age=month_salary_k_per_age,
        month_req_cost_k_per_age=month_req_cost_k_per_age,
        share_tax_per_k_salary=share_tax_per_k_salary,
        leak_multiplier_per_age=leak_multiplier_per_age
    )
    run_linear_optimization(conf)
    st.write(f"Lives saved: {conf.lives_saved}, Sum given: {conf.sum_given_m :.2f} [m] ")
    fig = conf.plot_summary()
    st.pyplot(fig)
