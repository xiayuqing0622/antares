# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import math
import logging
import copy
import random
import json
import time
import numpy as np
from itertools import combinations, permutations


class Parameter(object):
    """Base class for all types of parameters
    """
    def mutate(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def pick_out(self):
        raise NotImplementedError

    def get_cardinality(self):
        raise NotImplementedError

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False


class Choice(Parameter):
    """choice type parameter
    """
    def __init__(self, choices, mutate_rate, init=None):
        self.choices = choices
        self.mutate_rate = mutate_rate
        if init is not None:
            self.value = init
        else:
            self.value = random.choice(self.choices)

    def get_cardinality(self):
        return len(self.choices)

    def reset(self):
        self.value = random.choice(self.choices)

    def mutate(self):
        child = copy.deepcopy(self)
        while random.uniform(0, 1) < child.mutate_rate:
            choices = copy.deepcopy(child.choices)
            choices.remove(child.value)
            if choices:
                child.value = random.choice(choices)
            else:
                break

        return child

    def pick_out(self):
        return self.value


class Discrete(Parameter):
    """discrete type parameter
    """
    def __init__(self, numbers, mutate_rate, init=None):
        numbers.sort()
        self.numbers = numbers
        self.mutate_rate = mutate_rate
        if init is not None:
            self.value = init
        else:
            self.value = random.choice(self.numbers)

    def get_cardinality(self):
        return len(self.numbers)

    def reset(self):
        self.value = random.choice(self.numbers)

    def mutate(self):
        child = copy.deepcopy(self)
        while random.uniform(0, 1) < child.mutate_rate:
            idx = child.numbers.index(child.value)
            if idx == 0 and idx + 1 < len(child.numbers):
                child.value = child.numbers[idx + 1]
            elif idx + 1 == len(child.numbers) and idx - 1 >= 0:
                child.value = child.numbers[idx - 1]
            elif idx == 0 and idx + 1 == len(child.numbers):
                break
            else:
                shift = random.choice([-1, 1])
                child.value = child.numbers[idx + shift]

        return child

    def pick_out(self):
        return self.value


class Permutation(Parameter):
    """permutation type parameter
    """
    def __init__(self, value, mutate_rate, init=None):
        self.perms = []
        for perm in permutations(range(value)):
            self.perms.append(list(perm))
        self.mutate_rate = mutate_rate
        if init is not None:
            self.value = init
        else:
            self.value = random.choice(self.perms)

    def get_cardinality(self):
        return len(self.perms)

    def reset(self):
        self.value = random.choice(self.perms)

    def mutate(self):
        child = copy.deepcopy(self)
        while len(self.value) > 1 and random.uniform(0, 1) < child.mutate_rate:
            idx = list(range(len(self.value)))
            idx1 = random.choice(idx)
            idx.pop(idx1)
            idx2 = random.choice(idx)

            tmp = child.value[idx1]
            child.value[idx1] = child.value[idx2]
            child.value[idx2] = tmp

        return child

    def pick_out(self):
        return self.value


class Factor(Parameter):
    """factor type parameter
    """
    def __init__(self, value, mutate_rate, init=None):
        self.product, self.num = value
        self.mutate_rate = mutate_rate
        if init is not None:
            self.partition = init
        else:
            self.all_partitions = \
                self._get_all_partitions(self.product, self.num)
            self.partition = random.choice(self.all_partitions)

    def reset(self):
        if not hasattr(self, 'all_partitions'):
            self.all_partitions = \
                self._get_all_partitions(self.product, self.num)
        self.partition = random.choice(self.all_partitions)

    def get_cardinality(self):
        if not hasattr(self, 'all_partitions'):
            self.all_partitions = \
                self._get_all_partitions(self.product, self.num)
        return len(self.all_partitions)

    def mutate(self):
        child = copy.deepcopy(self)
        # print(child)
        while random.uniform(0, 1) < self.mutate_rate:
            action = random.choice(child._get_actions())
            child._step(action)

        return child

    def pick_out(self):
        return self.partition

    def _step(self, action):
        self.partition[action[0]] = int(self.partition[action[0]] / action[2])
        self.partition[action[1]] = int(self.partition[action[1]] * action[2])

    def _get_actions(self):
        actions = []
        prime_factors = self._get_prime_factors(self.product, False)
        for i in range(self.num):
            for j in range(self.num):
                if i != j:
                    for k in range(len(prime_factors)):
                        action = [i]
                        action.append(j)
                        action.append(prime_factors[k])
                        if self.partition[action[0]] % action[2] == 0:
                            actions.append(action)
        return actions

    def __repr__(self):
        string = "["
        for factor in self.partition:
            string += factor.__repr__() + " "
        string = string[:-1] + "]"

        return string

    def _get_all_partitions(self, product, num):
        # get all prime factors with repetition
        prime_factors = self._get_prime_factors(product)

        # group all prime factors
        groups = {}
        for prime_factor in prime_factors:
            if prime_factor in groups.keys():
                groups[prime_factor] += 1
            else:
                groups[prime_factor] = 1

        # partition each group
        for key, value in groups.items():
            partitions = []
            for comb in combinations(range(value + num - 1), num - 1):
                # print(comb)
                partition = []
                start_idx = -1
                for idx in comb:
                    partition.append(key**(idx - start_idx - 1))
                    start_idx = idx
                partition.append(key**(value + num - 2 - start_idx))
                partitions.append(partition)
            groups[key] = partitions

        # generate partitions
        partitions = []

        def part(groups, mul=[]):
            if not groups:
                partition = [1] * num
                for i in range(num):
                    for m in mul:
                        partition[i] *= m[i]
                partitions.append(partition)

            for key, group in groups.items():
                for partition in group:
                    mul.append(partition)
                    tmp = copy.deepcopy(groups)
                    del tmp[key]
                    part(tmp, mul)
                    mul.pop()
                break

        part(groups)
        return partitions

    def _get_prime_factors(self, n, repeat=True):
        prime_factors = []

        while n % 2 == 0:
            if 2 not in prime_factors:
                prime_factors.append(2)
            elif repeat:
                prime_factors.append(2)
            n = n / 2

        for i in range(3, int(math.sqrt(n)) + 1, 2):
            while n % i == 0:
                if i not in prime_factors:
                    prime_factors.append(i)
                elif repeat:
                    prime_factors.append(i)
                n = n / i

        if n > 2:
            prime_factors.append(int(n))

        return prime_factors


class Individual(object):
    """Individual class
    """
    def __init__(self, search_space, mutate_rate):
        self.params = {}
        for key in search_space.keys():
            if search_space[key]['_type'] == 'choice':
                if '_init' in search_space[key]:
                    self.params[key] = \
                        Choice(search_space[key]['_value'], mutate_rate,
                               search_space[key]['_init'])
                else:
                    self.params[key] = \
                        Choice(search_space[key]['_value'], mutate_rate)
            elif search_space[key]['_type'] == 'discrete':
                if '_init' in search_space[key]:
                    self.params[key] = \
                        Discrete(search_space[key]['_value'], mutate_rate,
                                 search_space[key]['_init'])
                else:
                    self.params[key] = \
                        Discrete(search_space[key]['_value'], mutate_rate)
            elif search_space[key]['_type'] == 'factor':
                if '_init' in search_space[key]:
                    self.params[key] = \
                        Factor(search_space[key]['_value'], mutate_rate,
                               search_space[key]['_init'])
                else:
                    self.params[key] = \
                        Factor(search_space[key]['_value'], mutate_rate)
            elif search_space[key]['_type'] == 'perm':
                if '_init' in search_space[key]:
                    self.params[key] = \
                        Permutation(search_space[key]['_value'], mutate_rate,
                                    search_space[key]['_init'])
                else:
                    self.params[key] = \
                        Permutation(search_space[key]['_value'], mutate_rate)
            else:
                raise RuntimeError(
                    "OpEvo Tuner doesn't support this kind of parameter: "
                    + str(search_space[key]['_type'])
                )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __repr__(self):
        string = ""
        for param in self.params:
            string += param.__repr__() + '\n'

        return string

    def mutate(self):
        child = copy.deepcopy(self)
        for key in child.params.keys():
            child.params[key] = child.params[key].mutate()

        return child

    def reset(self):
        for key in self.params.keys():
            self.params[key].reset()

        return self

    def pick_out(self):
        output = {}
        for key in self.params.keys():
            output[key] = self.params[key].pick_out()

        return output


class Population(object):
    """Population class
    """

    def __init__(self, search_space, mutate_rate, opt_mode='maximize'):
        self.search_space = search_space
        self.mutate_rate = mutate_rate
        self.opt_mode = opt_mode
        self.population = []
        self.fitness = []
        self.search_spaces = []

        def generate_search_space(ss, search_space):
            if search_space.keys():
                key = list(search_space.keys())[0]
            else:
                self.search_spaces.append(copy.deepcopy(ss))
                return
            ss[key] = {}
            ss[key]['_type'] = search_space[key]['_type']
            ss[key]['_value'] = search_space[key]['_value']
            if '_init' in search_space[key]:
                for init in search_space[key]['_init']:
                    ss[key]['_init'] = init
                    generate_search_space(ss,
                        {i: search_space[i] for i in search_space if i != key})
            else:
                generate_search_space(ss,
                    {i: search_space[i] for i in search_space if i != key})

        generate_search_space({}, self.search_space)

        self.individual = Individual(
            self.search_spaces[0], self.mutate_rate)

        self.volume = 1
        for key, value in self.individual.params.items():
            self.volume *= self.individual.params[key].get_cardinality()

    def append(self, individual, fitness):
        if self.opt_mode == "minimize":
            fitness = -1 * fitness

        self.population.insert(0, individual)
        self.fitness.insert(0, fitness)

        i = 0
        while (i < len(self.fitness) - 1
                and self.fitness[i] < self.fitness[i + 1]):
            self.fitness[i], self.fitness[i + 1] = \
                self.fitness[i + 1], self.fitness[i]
            self.population[i], self.population[i + 1] = \
                self.population[i + 1], self.population[i]
            i += 1

    def get_offspring(self, parents_size, offspring_size):
        children = []
        if len(self.fitness) < parents_size:
            while self.search_spaces:
                ss = self.search_spaces.pop()
                children.append(Individual(ss, self.mutate_rate))
            for _ in range(offspring_size - len(children)):
                child = copy.deepcopy(self.individual.reset())
                while child in self.population or child in children:
                    child = child.mutate()
                children.append(child)
        elif self.fitness[0] < 1e-3:
            for _ in range(offspring_size):
                child = copy.deepcopy(self.individual.reset())
                while child in self.population or child in children:
                    child = child.mutate()
                children.append(child)
        else:
            prob = np.array(self.fitness[:parents_size]) / \
                np.sum(self.fitness[:parents_size])

            for _ in range(offspring_size):
                child = copy.deepcopy(self.population[0])
                for key in child.params.keys():
                    idx = np.random.choice(range(parents_size), p=prob)
                    child.params[key] = self.population[idx].params[key]
                child = child.mutate()
                while child in self.population or child in children:
                    child = child.mutate()
                children.append(child)

        return children


from tvm.autotvm.tuner import Tuner
from tvm.autotvm.tuner.model_based_tuner import knob2point, point2knob

class MainTuner(Tuner):

    def __init__(self,
                 task,
                 batch_size=16,
                 optimize_mode="maximize",
                 parents_size=16,
                 offspring_size=16,
                 mutate_rate=0.5):
        """OpEvo Tuner

        Parameters
        ----------
        search_space: dict
        batch_size: int
        optimize_mode: str, 'maximize' or 'minimize'
        parents_size: int
            the amount of parents could transfer their character to offspring
        offspring_size: int
            the amount of offspring generated for each iteration
        mutate_rate: float, [0, 1]
            mutate rate q for each offspring,
            OpEvo tends to prefer exploration as q approaches 0 ,
            while OpEvo tends to prefer exploitation as q approaches 1

        Json Space Example:
        ---------
        search_space={
          'tile_x': {'_type': 'factor', '_value': [4096, 4], '_init': [[4096, 1, 1, 1], [2048, 2, 1, 1]]},
          'tile_y': {'_type': 'factor', '_value': [1024, 4], '_init': [[1024, 1, 1, 1], [512, 2, 1, 1]]},
          'tile_k': {'_type': 'factor', '_value': [64, 3]},
          'unroll': {'_type': 'choice', '_value': [0, 1]},
          'num': {'_type': 'discrete', '_value': [1, 2, 3, 4, 5], '_init': [1, 2, 3]},
          'reorder': {'_type': 'perm', '_value': 3, '_init': [[0, 1, 2], [1, 2, 0]]},
        }
        """
        super(MainTuner, self).__init__(task)

        self.logger = logging.getLogger(
            self.__module__ + "." + self.__class__.__name__
        )
        self.logger.setLevel('DEBUG')
        self.logger.info('Tuner.__init__(...)')

        self.batch_size = batch_size
        self.optimize_mode = optimize_mode
        self.parents_size = parents_size
        self.offspring_size = offspring_size
        self.mutate_rate = mutate_rate

        self.serve_list = []
        self.wait_dict = {}

        self.search_space = self.task.antares_helper.to_json_search_space(self.task.config_space)
        self.logger.info('Search space =', self.search_space)
        self._update_search_space(self.search_space)

    def _update_search_space(self, search_space):
        """Update search space

        Parameters
        ----------
        search_space : dict
        """
        if not isinstance(search_space, dict):
            self.logger.info("The format of search space is not a dict.")
            raise RuntimeError("The format of search space is not a dict.")

        self.population = Population(
            search_space,
            self.mutate_rate,
            self.optimize_mode
        )
        self.logger.debug('Total search space volume: '
                          + str(self.population.volume))
        self.logger.info('Total search space volume: '
                          + str(self.population.volume))

        if not self.serve_list:
            self.serve_list = self.population.get_offspring(
                self.parents_size, self.offspring_size)

    def next_batch(self, batch_size):
        self.logger.info('Tuner.next_batch()')
        self.batch_size = batch_size
        res = []
        for candidate in self.serve_list[:self.batch_size]:
            cand_final = copy.deepcopy(candidate.pick_out())
            for key in cand_final:
                if self.search_space[key]['_type'] == 'factor':
                    cand_final[key][0] = -1

            cand_json = json.dumps(cand_final)
            self.wait_dict[cand_json] = candidate

            res.append(self.task.antares_helper.json_to_config(cand_final, code_hash=cand_json))

        self.serve_list = self.serve_list[self.batch_size:]
        return res

    def update(self, inputs, results):
        self.logger.info('Tuner.update(...)')
        for conf, perf in zip(inputs, results):
            conf, perf = conf.config.code_hash, float(np.mean(perf.costs))
            try:
                self.population.append(self.wait_dict[conf], self.task.flop / perf)
            except:
                pass
            self.wait_dict.pop(conf, None)

        if len(self.serve_list) < self.batch_size:
            self.serve_list.extend(
                self.population.get_offspring(
                    self.parents_size, self.offspring_size
                )[:self.batch_size - len(self.serve_list)])

    def has_next(self):
      return len(self.serve_list) > 0

    def load_history(self, data_set):
        pass

