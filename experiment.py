# Copying imports from the modes experiment. Will remove unused ones later. Adding others as needed.
import random
from random import randint

from dominate import tags
from numpy import isnan

import psynet.experiment
from psynet.js_synth import JSSynth, InstrumentTimbre, Note, ShepardTimbre, Chord
from psynet.modular_page import SurveyJSControl, PushButtonControl
from psynet.page import InfoPage, SuccessfulEndPage, ModularPage
from psynet.prescreen import AntiphaseHeadphoneTest
from psynet.timeline import Timeline, Event
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
    #Dyads
    [0, 1],
    [0, 2],
    [0, 3],
    [0, 4],
    [0, 5],
    [0, 6],

    #Triads
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

    #Quartads
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

RATING_ATTRIBUTES = {   # 15 in total
    'Happiness, elation',
    'Sadness, melancholy',
    'Surprise, astonishment',
    'Calm, contentment',
    'Anger, irritation',
    'Nostalgia, longing',
    'Interest, expectancy',
    'Anxiety, nervousness',
    'Love, tenderness',
    'Disgust, contempt',
    'Spirituality, transcendence',
    'Admiration, awe',
    'Enjoyment, pleasure',
    'Pride, confidence',
    'Boredom, indifference',
}

N_RATING_ATTRIBUTES_PER_TRIAL = 1 #Quickfire trials.
TRIALS_PER_PARTICIPANT = 100 #Just a placeholder. At 5 sec per trial = 8.33 minutes of rating.
N_REPEAT_TRIALS = 5

NODES = [
    StaticNode(
        definition={
            "chord": chord,
            "rating_attribute": rating_attribute
        },
    )
    for chord in CHORDS
    for rating_attribute in RATING_ATTRIBUTES
]

class ChordTrial(StaticTrial):
    time_estimate = 5

    @property
    def base_chord(self):
        return self.definition["chord"]

    def rating_attribute(self):
        return self.definition["rating_attribute"]

    def finalize_definition(self, definition, experiment, participant):
        definition["duration"] = 5
        definition["base_pitch"] = randint(54, 66) #Considering whether one 8ve is enough.

        #TODO: work out correct way to refer to chord.
        definition["realized_chord"] = [int(note) + definition["base_pitch"]
                          for note in self.base_chord]

        return definition

    def show_trial(self, experiment, participant):
        return ModularPage(
            "rating",
            JSSynth(
                (
                    f"Rate this chord on the following scale: {self.definition['rating_attribute']}"
                ),
                [
                    Chord(self.definition["realized_chord"],
                          duration=self.definition["duration"])
                ],
                timbre=TIMBRE,
            ),
            PushButtonControl(
                ["1", "2", "3", "4", "5"],
                arrange_vertically=False,
                bot_response=randint(1,5),
            ),
        )

class ChordsTrialMaker(StaticTrialMaker):
    give_end_feedback_passed = False

    def performance_check(
        self, experiment, participant, participant_trials
    ):
        trials_by_id = {trial.id: trial for trial in participant_trials}

        repeat_trials = [t for t in participant_trials if t.is_repeat_trial]
        parent_trials = [trials_by_id[t.parent_trial_id] for t in repeat_trials]

        repeat_trial_answers = []
        parent_trial_answers = []

        for repeat_trial, parent_trial in zip(repeat_trials, parent_trials):
            assert repeat_trial.definition["rating_attributes"] == parent_trial.definition["rating_attributes"]

            repeat_trial_answers.append(int(repeat_trial.answer))
            parent_trial_answers.append(int(parent_trial.answer))

        consistency = corr(repeat_trial_answers, parent_trial_answers, method="spearman")
        passed = True

        if isnan(consistency):
            consistency = None

        logger.info(
            "Performance check for participant %i: consistency = %.1f%%, passed = %s",
            participant.id,
            consistency * 100.0,
            passed,
        )

        return {"score": consistency, "passed": passed}

    def compute_bonus(self, score, passed):
        max_bonus = 0.40

        if score is None or score <= 0.0:
            bonus = 0.0
        else:
            bonus = max_bonus * score

        bonus = min(bonus, max_bonus)
        return bonus


class Exp(psynet.experiment.Experiment):
    label = "chord exp in progress",
    test_n_bots = 5

#I'm leaving the instructions, questionnaire, and debriefing out of the timeline for now (and the audio checks).
#But, I'm making some changes to wording in them to reflect this experiment.
    timeline = Timeline(
        NoConsent(),
        ChordsTrialMaker(
            id_= "main_experiment",
            trial_class = ChordTrial,
            nodes = NODES,
            expected_trials_per_participant=TRIALS_PER_PARTICIPANT,
            max_trials_per_participant=TRIALS_PER_PARTICIPANT,
            recruit_mode="n_participants",
            allow_repeated_nodes=False,
            n_repeat_trials=N_REPEAT_TRIALS,
            balance_across_nodes=False,
            target_n_participants=50,
            check_performance_at_end=False,
        ),
        SuccessfulEndPage(),
    )
