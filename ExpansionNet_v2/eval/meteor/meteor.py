#!/usr/bin/env python

# Python wrapper for METEOR implementation, by Xinlei Chen
# Acknowledge Michael Denkowski for the generous discussion and help 

# modified according to: https://github.com/tylin/coco-caption/issues/27
# to support python3.5

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import subprocess
import threading

# Assumes meteor-1.5.jar is in the same directory as meteor.py.  Change as needed.
METEOR_JAR = 'meteor-1.5.jar'


# print METEOR_JAR

class Meteor:

    def __init__(self):
        self.env = os.environ
        self.env['LC_ALL'] = 'en_US.UTF_8'
        self.meteor_cmd = ['java', '-jar', '-Xmx2G', METEOR_JAR,
                           '-', '-', '-stdio', '-l', 'en', '-norm']
        self.meteor_p = subprocess.Popen(self.meteor_cmd,
                                         cwd=os.path.dirname(os.path.abspath(__file__)),
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         env=self.env, universal_newlines=True, bufsize=1)
        # Used to guarantee thread safety
        self.lock = threading.Lock()

    def compute_score(self, gts, res):
        assert (gts.keys() == res.keys())
        imgIds = sorted(list(gts.keys()))
        scores = []

        eval_line = 'EVAL'
        self.lock.acquire()
        for i in imgIds:
            assert (len(res[i]) == 1)
            # There's a situation that the prediction is all punctuations
            # (see definition of PUNCTUATIONS in pycocoevalcap/tokenizer/ptbtokenizer.py)
            # then the prediction will become [''] after tokenization
            # which means res[i][0] == '' and self._stat will failed with this input
            if len(res[i][0]) == 0:
                res[i][0] = 'a'
            stat = self._stat(res[i][0], gts[i])
            eval_line += ' ||| {}'.format(stat)

        # Send to METEOR
        self.meteor_p.stdin.write(eval_line + '\n')

        # Collect segment scores
        for i in range(len(imgIds)):
            score = float(self.meteor_p.stdout.readline().strip())
            scores.append(score)

        # Final score
        final_score = float(self.meteor_p.stdout.readline().strip())
        self.lock.release()

        return final_score, scores

    def method(self):
        return "METEOR"

    def _stat(self, hypothesis_str, reference_list):
        # SCORE ||| reference 1 words ||| reference n words ||| hypothesis words
        hypothesis_str = hypothesis_str.replace('|||', '').replace('  ', ' ')
        if sys.version_info[0] == 2:  # python2
            score_line = ' ||| '.join(('SCORE', ' ||| '.join(reference_list), hypothesis_str)).encode('utf-8').strip()
            self.meteor_p.stdin.write(str(score_line + b'\n'))
        else:  # assume python3+
            score_line = ' ||| '.join(('SCORE', ' ||| '.join(reference_list), hypothesis_str)).strip()
            self.meteor_p.stdin.write(score_line + '\n')
        return self.meteor_p.stdout.readline().strip()

    def __del__(self):
        self.lock.acquire()
        self.meteor_p.stdin.close()
        self.meteor_p.kill()
        self.meteor_p.wait()
        self.lock.release()