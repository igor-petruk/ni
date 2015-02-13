import unittest

from nibt import common, graph
import functools
import logging

class DependencyTrackerTest(unittest.TestCase):
    def GetDeps1(self, target):
        d = {
            "a": set(["b", "c"]),
            "b": set(["d"]),
            "d": set(["c"]),
            "c": set(["e"]),
            "e": set(["f"]),
        }
        return d.get(target, set())
    
    def setUp(self):
        self.deps1 = functools.partial(DependencyTrackerTest.GetDeps1, self)
        self.d = graph.DependencyTracker(self.deps1)

    def testAddTopLevelTarget(self):
        logging.info("AddedTopLevelTarget a: %s", self.d.AddTopLevelTarget("a"))
        logging.info("AddedTopLevelTarget b: %s", self.d.AddTopLevelTarget("b"))
        logging.info("RemovedTopLevelTarget a: %s", self.d.RemoveTopLevelTarget("a"))
        logging.info("RefreshedTarget d: %s",self.d.RefreshTarget("d"))
        logging.info("RefreshedTarget c: %s",self.d.RefreshTarget("c"))
        logging.info("RefreshedTarget e: %s",self.d.RefreshTarget("e"))
        logging.info("RefreshedTarget b`: %s",self.d.RefreshTarget("b"))

if __name__ == '__main__':
    unittest.main()
