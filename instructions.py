from dominate import tags

from psynet.page import InfoPage


def instructions():
    html = tags.div()

    with html:
        tags.p(
            """
            In this experiment you will listen to a series of chords.
            You will be asked to rate how well each chord matches a pair of words,
            for example "Happiness, elation".
            """
        )

        tags.p(
            """
            Take as much time as you need for each question. The chord will play for 5 seconds, but you are free to 
            consider your answer for a longer time before selecting a number.
            """
        )

        tags.p(
            """
            We will monitor the answers you give throughout the experiment, and will give a small additional bonus
            if you give high-quality and reliable responses. Listen carefully and give it your best shot!
            """
        )

        tags.p(
            """
            Press 'Next' when you are ready to continue.
            """
        )

    return InfoPage(html, time_estimate=15)
