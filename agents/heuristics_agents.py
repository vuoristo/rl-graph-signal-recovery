import numpy as np
from agents import BaseAgent
from algorithms.recovery import sparse_label_propagation
from graph_functions import nmse
from collections import defaultdict

class SimpleHeuristicsAgent(BaseAgent):
  def __init__(self, env, num_train_graphs):
    self.env = env
    self._num_train_graphs = num_train_graphs
    self.sampling_list = []
    self.node_data = {}

  def sort_partition(self, partition):
    graph = self.env.graph
    boundary_degrees = defaultdict(list)
    degrees = graph.degree()
    for node in partition:
      boundary_degree = len(
          [n for n in graph.neighbors(node)
           if n not in partition])
      boundary_degrees[boundary_degree].append(node)
      self.node_data[node] = {'bd': boundary_degree,
                              'degree': degrees[node],
                              'partition_size': len(partition)}

    sorted_boundary_degrees = sorted(boundary_degrees.keys())
    sorted_nodes = []
    for degree in sorted_boundary_degrees:
      degree_nodes = boundary_degrees[degree]
      global_degree_indices = np.argsort([degrees[i] for i in degree_nodes])
      global_degree_sorted = [degree_nodes[i] for i in global_degree_indices]
      sorted_nodes += global_degree_sorted
    return sorted_nodes

  def compute_sampling_list(self):
    self.sampling_list = []
    graph = self.env.graph
    partitions = graph.graph['partition']
    partition_lists = []
    for partition in partitions:
      partition_nodes = [node for node in partition if node in graph.nodes()]
      if len(partition_nodes) > 0:
        partition_lists.append(partition_nodes)
    partition_size = [len(partition) for partition in partition_lists]
    partition_indices = np.argsort(partition_size)
    ordered_partitions = [partition_lists[i] for i in partition_indices
                          if len(partition_lists[i]) > 0]
    internally_sorted_partitions = []
    for partition in ordered_partitions:
      sorted_partition = self.sort_partition(partition)
      internally_sorted_partitions.append(sorted_partition)

    sampling_list = []
    internally_sorted_partitions = list(reversed(internally_sorted_partitions))
    for i in range(graph.number_of_nodes()):
      partition_index = i % len(partition_lists)
      if len(internally_sorted_partitions[partition_index]) > 0:
        next_node = internally_sorted_partitions[partition_index].pop()
        sampling_list.append(next_node)

    self.sampling_list = list(reversed(sampling_list))

  def act(self, observation):
    """Return the next node from the precomputed sampling set."""
    if len(self.env.sampling_set) == 0:
      self.compute_sampling_list()

    if len(self.sampling_list) > 0:
      next_node = self.sampling_list.pop()
      self.env.sampling_set.add(next_node)
      return 1
    else:
      return 0

  def learn(self):
    raise NotImplementedError('SimpleHeuristicsAgent does not need training')

  def test(self):
    env = self.env
    act = self.act
    nmses = []
    for i in range(self._num_train_graphs):
      observation, done = env.reset(), False
      while not done:
        action = act(observation[None])
        observation, reward, done, _ = env.step(action)

      graph = env.graph
      x = [graph.node[i]['value'] for i in range(graph.number_of_nodes())]
      sampling_set = env.sampling_set
      x_hat = sparse_label_propagation(graph, list(sampling_set))

      graph_error = nmse(x, x_hat)
      print("nmse: {}".format(graph_error))
      nmses.append(graph_error)

    print('mean nmse', np.mean(nmses))