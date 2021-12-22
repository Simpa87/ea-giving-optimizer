from ea_giving_optimizer.helpers import remains, tot_give


def test_remains():

    assert round(remains(
        disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
        give_share={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0},
        i=6,
        r=1.1
    ), 2) == round(1.1**5 + 1.1**4 + 1.1**3 + 1.1**2 + 1.1**1, 2)

    assert remains(
        disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
        give_share={1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 0},  # Give all at step 5 => 0
        i=6,
        r=1.1
    ) == 0

    assert remains(
        disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
        give_share={1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 0},  # Give all at step 5 => 0
        i=6,
        r=1.1
    ) == 1.1


def test_tot_give():
    assert round(
        tot_give(
            disp={1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
            give_share={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1},
            r=1.1),
        2) == round(1.1 ** 6 + 1.1 ** 5 + 1.1 ** 4 + 1.1 ** 3 + 1.1 ** 2 + 1.1 ** 1, 2)
