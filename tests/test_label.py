from kachi_sense.label import SOURCE, TARGET, Trial, label_trial

T = Trial("t1", t_start=10.0, t_grasp=11.0, t_end=14.0)


def ev(ch, t):
    return {"ch": ch, "t": t, "peak": 100.0}


def test_success():
    assert label_trial(T, [ev(TARGET, 12.5)])["result"] == "success"


def test_drop_back_to_source():
    assert label_trial(T, [ev(SOURCE, 11.4)])["result"] == "dropped"


def test_source_click_before_grasp_is_ignored():
    assert label_trial(T, [ev(SOURCE, 10.5), ev(TARGET, 12.0)])["result"] == "success"


def test_two_beans():
    assert label_trial(T, [ev(TARGET, 12.0), ev(TARGET, 12.4)])["result"] == "double"


def test_miss():
    assert label_trial(T, [ev(TARGET, 15.0)])["result"] == "miss"
