from concurrent.futures import ThreadPoolExecutor

import athreading

TEST_VALUES = [1, None, "", 2.0]

executor = ThreadPoolExecutor()


def generator(delay=0.0, repeats=1):
    for _ in range(repeats):
        yield from TEST_VALUES


@athreading.iterate(executor=executor)
def aiterate(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.iterate()
def aiterate_simpler(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.iterate
def aiterate_simplest(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.generate(executor=executor)
def agenerate(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.generate()
def agenerate_simpler(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


@athreading.generate
def agenerate_simplest(delay=0.0, repeats=1):
    yield from generator(delay, repeats)


def test_call_attrs():
    assert aiterate.__name__ == "aiterate"
    assert aiterate_simpler.__name__ == "aiterate_simpler"
    assert aiterate_simplest.__name__ == "aiterate_simplest"


def test_iterate_attrs():
    assert aiterate.__name__ == "aiterate"
    assert aiterate_simpler.__name__ == "aiterate_simpler"
    assert aiterate_simplest.__name__ == "aiterate_simplest"


def test_generate_attrs():
    assert agenerate.__name__ == "agenerate"
    assert agenerate_simpler.__name__ == "agenerate_simpler"
    assert agenerate_simplest.__name__ == "agenerate_simplest"
