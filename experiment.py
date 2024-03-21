# Copying imports from the modes experiment. Will remove unused ones later. Adding others as needed.
import random
from random import randint

from dominate import tags
from numpy import isnan
from markupsafe import Markup

import psynet.experiment
from psynet.js_synth import JSSynth, InstrumentTimbre, Note, ShepardTimbre, Chord
from psynet.modular_page import SurveyJSControl, PushButtonControl
from psynet.page import InfoPage, SuccessfulEndPage, ModularPage, WaitPage, UnsuccessfulEndPage
from psynet.prescreen import AntiphaseHeadphoneTest
from psynet.timeline import Timeline, Event, conditional, join
from psynet.trial.static import StaticTrial, StaticNode, StaticTrialMaker
from psynet.utils import get_logger, corr
from psynet.bot import Bot

from .consent import consent, NoConsent
from .debrief import debriefing
from .instructions import instructions
from .questionnaire import questionnaire, questionnaire_intro
from .stimuli import load_scales, load_melodies
from .volume_calibration import volume_calibration

logger = get_logger()

TIMBRE = ShepardTimbre()

CHORDS = [
    # Dyads
    [0, 1],
    [0, 2],
    [0, 3],
    [0, 4],
    [0, 5],
    [0, 6],

    # Triads
    [0, 1, 2],
    [0, 1, 3],
    [0, 1, 4],
    [0, 1, 5],
    [0, 1, 6],

    [0, 2, 3],
    [0, 2, 4],
    [0, 2, 5],
    [0, 2, 6],
    [0, 2, 7],

    [0, 3, 4],
    [0, 3, 5],
    [0, 3, 6],
    [0, 3, 7],

    [0, 4, 5],
    [0, 4, 6],
    [0, 4, 7],
    [0, 4, 8],

    [0, 5, 6],

    # Quartads
    [0, 1, 2, 3],
    [0, 1, 2, 4],
    [0, 1, 2, 5],
    [0, 1, 2, 6],
    [0, 1, 2, 7],

    [0, 1, 3, 4],
    [0, 1, 3, 5],
    [0, 1, 3, 6],
    [0, 1, 3, 7],

    [0, 1, 4, 5],
    [0, 1, 4, 6],
    [0, 1, 4, 7],
    [0, 1, 4, 8],

    [0, 1, 5, 6],
    [0, 1, 5, 7],
    [0, 1, 5, 8],

    [0, 1, 6, 7],

    [0, 2, 3, 4],
    [0, 2, 3, 5],
    [0, 2, 3, 6],
    [0, 2, 3, 7],

    [0, 2, 4, 5],
    [0, 2, 4, 6],
    [0, 2, 4, 7],
    [0, 2, 4, 8],

    [0, 2, 5, 6],
    [0, 2, 5, 7],
    [0, 2, 5, 8],

    [0, 2, 6, 7],
    [0, 2, 6, 8],

    [0, 3, 4, 5],
    [0, 3, 4, 6],
    [0, 3, 4, 7],
    [0, 3, 4, 8],

    [0, 3, 5, 6],
    [0, 3, 5, 7],
    [0, 3, 5, 8],

    [0, 3, 6, 7],
    [0, 3, 6, 8],
    [0, 3, 6, 9],

    [0, 4, 5, 6],
    [0, 4, 5, 7],

    [0, 4, 6, 7]
]

TRIALS_PER_PARTICIPANT = 68
N_REPEAT_TRIALS = 68
BREAK_AFTER_N_TRIALS = 68

NODES = [
    StaticNode(
        definition={
            "chord": chord
        },
    )
    for chord in CHORDS
]


class ChordTrial(StaticTrial):
    time_estimate = 3

    @property
    def base_chord(self):
        return self.definition["chord"]

    # def rating_attribute(self):
    #     return self.definition["rating_attribute"]

    def finalize_definition(self, definition, experiment, participant):
        definition["duration"] = 3
        definition["base_pitch"] = randint(60, 71)

        # TODO: work out correct way to refer to chord.
        definition["realized_chord"] = [note + definition["base_pitch"]
                                        for note in self.base_chord]

        return definition

    def get_bot_response(self, bot):
        if self.is_repeat_trial:
            parent = ChordTrial.query.get(self.parent_trial_id)
            return parent.answer
        else:
            return self.generate_answer(bot)

    def generate_answer(self, bot):
        match bot.id % 4:  # 4 different responding styles
            case 0: #Static response
                return 3
            case 1: #Random response
                return randint(1, 5)
            case 2: #Response == numerosity
                return len(self.base_chord)
            case 3: #Seventh-chord fan
                if (2 or 10) in self.base_chord:
                    return 5
                else:
                    return 1

    def show_trial(self, experiment, participant):
        trial_page = ModularPage(
            "rating",
            JSSynth(
                (
                    Markup("""
                    <p>
                    How pleasant is this chord? 
                    </p>
                    """
                           )
                ),
                [
                    Chord(self.definition["realized_chord"],
                          duration=self.definition["duration"])
                ],
                timbre=TIMBRE,
                text_align="center",
            ),
            PushButtonControl(
                [1, 2, 3, 4, 5],
                ["Very unpleasant", "Somewhat unpleasant", "Neutral", "Somewhat pleasant", "Very pleasant"],
                arrange_vertically=False,
                bot_response=self.get_bot_response,
                style="width: 150px; margin: 10px",
            ),
            time_estimate=3,
        )

        break_page = WaitPage(
            wait_time=20,
            content="Please relax for a few moments, we will continue the experiment shortly.",
        )

        if self.position != 0 and self.position % BREAK_AFTER_N_TRIALS == 0:
            return join(break_page, trial_page)
        else:
            return trial_page


class ChordsTrialMaker(StaticTrialMaker):
    performance_check_type = "consistency"
    consistency_check_type = "spearman_correlation"
    give_end_feedback_passed = False

    def compute_performance_reward(self, score, passed):
        max_bonus = 0.40

        if score is None or score <= 0.0:
            bonus = 0.0
        else:
            bonus = max_bonus * score

        bonus = min(bonus, max_bonus)
        return bonus


class Exp(psynet.experiment.Experiment):
    label = "Chord pleasantness experiment"
    test_n_bots = 100

    timeline = Timeline(
        consent,
        InfoPage(
            tags.div(
                tags.p("This experiment requires you to wear headphones. Please ensure you have plugged yours in now."),
                tags.p("The next page will play some test audio. Please turn down your volume before proceeding.")
            ),
            time_estimate=5,
        ),
        volume_calibration(mean_pitch=67, sd_pitch=5, timbre=TIMBRE),
        InfoPage(
            """
            We will now perform a short listening test to verify that your audio is working properly.
            This test will be difficult to pass unless you listen carefully over your headphones.
            Press 'Next' when you are ready to start.
            """,
            time_estimate=5,
        ),
        AntiphaseHeadphoneTest(performance_threshold=0),
        instructions(),
        ChordsTrialMaker(
            id_="main_experiment",
            trial_class=ChordTrial,
            nodes=NODES,
            expected_trials_per_participant=TRIALS_PER_PARTICIPANT,
            max_trials_per_participant=TRIALS_PER_PARTICIPANT,
            recruit_mode="n_participants",
            allow_repeated_nodes=False,
            n_repeat_trials=N_REPEAT_TRIALS,
            balance_across_nodes=False,
            target_n_participants=100,
            check_performance_at_end=True,
        ),
        questionnaire_intro(),
        questionnaire(),
        debriefing(),
        SuccessfulEndPage(),
    )

    def test_check_bot(self, bot: Bot, **kwargs):
        module_state = bot.module_states["main_experiment"][0]
        performance_check = module_state.performance_check
        assert performance_check is not None
        assert performance_check["score"] == 1.0
        assert performance_check["passed"]
        assert bot.performance_reward > 0.0

        chord_trials = [t for t in bot.alive_trials if isinstance(t, ChordTrial)]
        assert len(chord_trials) == TRIALS_PER_PARTICIPANT * 2
