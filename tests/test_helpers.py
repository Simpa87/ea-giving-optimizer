from ea_giving_optimizer.helpers import remains, tot_give


def test_remains_simple():

    assert remains(
        disp={1: 1, 2: 2, 3: 3},
        give_share={1: 0, 2: 0, 3: 0},
        i=3,
        r=1
    ) == 1 + 2 + 3

    assert remains(
        disp={7: 1, 8: 2},
        give_share={7: 0.36, 8: 0.41},
        i=8,
        r=1
    ) == (1 - 0.36 + 2) * (1 - 0.41)


def test_remains_interest():

    assert round(remains(
        disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
        give_share={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0},
        i=6,
        r=1.1
    ), 2) == round(1.1**6 + 1.1**5 + 1.1**4 + 1.1**3 + 1.1**2 + 1.1**1, 2)  # All steps interest

    assert remains(
        disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
        give_share={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1},  # Give all at step 6 => 0
        i=6,
        r=1.1
    ) == 0

    assert remains(
        disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 0},
        give_share={1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 0},
        i=6,
        r=1.1
    ) == 1.1**2  # 2 steps of interest from step 5 to step 6


def test_tot_give_interest():
    assert round(
        tot_give(
            disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
            give_share={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1},
            r=1.1),
        2) == round(1.1 ** 6 + 1.1 ** 5 + 1.1 ** 4 + 1.1 ** 3 + 1.1 ** 2 + 1.1 ** 1, 2)


def test_tot_give_various_amounts():
    assert round(
        tot_give(
            disp={1: 1, 2: 1.12},
            give_share={1: 0.5, 2: 0.5},
            r=1),
        2) == round(1*0.5 + 0.5*(0.5 + 1.12), 2)


def test_tot_give_with_leaking():

    # No interest
    assert round(tot_give(
        disp={1: 1.11, 2: 2.22},
        give_share={1: 1, 2: 1},
        r=1,
        leak_mult={1: 0.99, 2: 0.88}
    ), 2) == round(1.11 * 0.99 + 2.22 * 0.88, 2)

    # With interest - Note that leaking is applied only to the age when given
    r = 1
    assert round(tot_give(
        disp={1: 1, 2: 1.1},
        give_share={1: 0.4, 2: 0.5},
        r=r,
        leak_mult={1: 0.49, 2: 0.45}
    ), 2) == round(0.4 * 0.49 * r ** 2 + (0.6 + 1.1) * 0.5 * 0.45 * r ** 1, 2)
