from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from six.moves import urllib
from six.moves import xrange  # pylint: disable=redefined-builtin
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

import collections
import math
import os
import random
import zipfile
import sklearn
import numpy as np
import tensorflow as tf
import pickle
import cPickle
import gzip
import datetime
import bz2

class SkipGram(object):
	def __init__(self):
		self.data = None
		self.count = None
		self.dictionary = None
		self.reverse_dictionary = None
		self.final_embeddings = None
		self.low_dim_embs = None
		self.clustered_synonyms = None
		self.batch = None
		self.labels = None
		self.data_index = 0

	def maybe_download(self, filename, expected_bytes):
		url = 'http://mattmahoney.net/dc/'
		"""Download a file if not present, and make sure it's the right size."""
		if not os.path.exists(filename):
			filename, _ = urllib.request.urlretrieve(url + filename, filename)
		statinfo = os.stat(filename)
		if statinfo.st_size == expected_bytes:
			print('Found and verified', filename)
		else:
			print(statinfo.st_size)
			raise Exception('Failed to verify ' + filename + '. Can you get to it with a browser?')

		return filename

	# Read the data into a list of strings.
	def read_data(self, filename):
		"""Extract the first file enclosed in a zip file as a list of words."""
		with zipfile.ZipFile(filename) as f:
			data = tf.compat.as_str(f.read(f.namelist()[0])).split()
			index = 1
			while index < len(f.namelist()):
				moredata = tf.compat.as_str(f.read(f.namelist()[index])).split()
				data = data.extend(moredata)

		return data

	def build_dataset(self, words, n_words):
	  """Process raw inputs into a dataset."""
	  count = [['UNK', -1]]
	  count.extend(collections.Counter(words).most_common(n_words - 1))
	  dictionary = dict()
	  for word, _ in count:
	    dictionary[word] = len(dictionary)
	  data = list()
	  unk_count = 0
	  for word in words:
	    if word in dictionary:
	      index = dictionary[word]
	    else:
	      index = 0  # dictionary['UNK']
	      unk_count += 1
	    data.append(index)
	  count[0][1] = unk_count
	  reversed_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
	  
	  return data, count, dictionary, reversed_dictionary

	# Step 3: Function to generate a training batch for the skip-gram model.
	def generate_batch(self, batch_size, num_skips, skip_window):
	  #global data_index
	  assert batch_size % num_skips == 0
	  assert num_skips <= 2 * skip_window
	  batch = np.ndarray(shape=(batch_size), dtype=np.int32)
	  labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
	  span = 2 * skip_window + 1  # [ skip_window target skip_window ]
	  buffer = collections.deque(maxlen=span)
	  for _ in range(span):
	    buffer.append(self.data[self.data_index])
	    self.data_index = (self.data_index + 1) % len(self.data)
	  for i in range(batch_size // num_skips):
	    target = skip_window  # target label at the center of the buffer
	    targets_to_avoid = [skip_window]
	    for j in range(num_skips):
	      while target in targets_to_avoid:
	        target = random.randint(0, span - 1)
	      targets_to_avoid.append(target)
	      batch[i * num_skips + j] = buffer[skip_window]
	      labels[i * num_skips + j, 0] = buffer[target]
	    buffer.append(self.data[self.data_index])
	    self.data_index = (self.data_index + 1) % len(self.data)
	  # Backtrack a little bit to avoid skipping words in the end of a batch
	  self.data_index = (self.data_index + len(self.data) - span) % len(self.data)
	  return batch, labels

	def plot_with_labels(self, low_dim_embs, labels, filename='tsne.png'):
	  assert low_dim_embs.shape[0] >= len(labels), 'More labels than embeddings'
	  plt.figure(figsize=(18, 18))  # in inches
	  for i, label in enumerate(labels):
	    x, y = low_dim_embs[i, :]
	    plt.scatter(x, y)
	    plt.annotate(label,
	                 xy=(x, y),
	                 xytext=(5, 2),
	                 textcoords='offset points',
	                 ha='right',
	                 va='bottom')

	  plt.savefig(filename)

	def train(self, filename=None):

		#if no specific vocabulary entered, use default vocabulary data
		#this looks kinda ugly but we can fix it later
		if filename is None:
			print('all good')
			filename = self.maybe_download('text8.zip', 31344016)

		'''the use of maybe_download() and read_data() for generating the vocabulary will be replaced by a simpler method that doesnt require reading from a file'''
		vocabulary = self.read_data(filename)
		print('Data size', len(vocabulary))
		
		# Step 2: Build the dictionary and replace rare words with UNK token.
		vocabulary_size = 100000
		'''from the vocabulary, extract @vocabulary_size words which are most common to construct the dataset'''
		self.data, self.count, self.dictionary, self.reverse_dictionary = self.build_dataset(vocabulary, vocabulary_size)
		del vocabulary  # Hint to reduce memory.

		print('Most common words (+UNK)', self.count[:5])
		print('Sample data', self.data[:10], [self.reverse_dictionary[i] for i in self.data[:10]])

		self.data_index = 0

		self.batch, self.labels = self.generate_batch(batch_size=8, num_skips=2, skip_window=1)
		for i in range(8):
		  print(self.batch[i], self.reverse_dictionary[self.batch[i]],
		        '->', self.labels[i, 0], self.reverse_dictionary[self.labels[i, 0]])

		# Step 4: Build and train a skip-gram model.

		batch_size = 128
		embedding_size = 128  # Dimension of the embedding vector.
		skip_window = 1       # How many words to consider left and right.
		num_skips = 2         # How many times to reuse an input to generate a label.

		# We pick a random validation set to sample nearest neighbors. Here we limit the
		# validation samples to the words that have a low numeric ID, which by
		# construction are also the most frequent.
		valid_size = 16     # Random set of words to evaluate similarity on.
		valid_window = 100  # Only pick dev samples in the head of the distribution.
		valid_examples = np.random.choice(valid_window, valid_size, replace=False)
		num_sampled = 64    # Number of negative examples to sample.

		graph = tf.Graph()

		with graph.as_default():

		  # Input data.
		  train_inputs = tf.placeholder(tf.int32, shape=[batch_size])
		  train_labels = tf.placeholder(tf.int32, shape=[batch_size, 1])
		  valid_dataset = tf.constant(valid_examples, dtype=tf.int32)

		  # Ops and variables pinned to the CPU because of missing GPU implementation
		  with tf.device('/cpu:0'):
		    # Look-up embeddings for inputs.
		    '''the @embeddings matrix is randomly generated such that each word in @vocabulary has its own distinct vector of dimension @embedding_size. The goal is to train on the @embeddings matrix'''
		    embeddings = tf.Variable(
		        tf.random_uniform([vocabulary_size, embedding_size], -1.0, 1.0))

		    '''associates each word embedding in @embeddings with its word from @train_inputs'''
		    embed = tf.nn.embedding_lookup(embeddings, train_inputs)

		    # Construct the variables for the NCE loss
		    '''weights and biases for each word embedding in @embeddings; training on these'''
		    nce_weights = tf.Variable(
		        tf.truncated_normal([vocabulary_size, embedding_size],
		                            stddev=1.0 / math.sqrt(embedding_size)))
		    nce_biases = tf.Variable(tf.zeros([vocabulary_size]))

		  # Compute the average NCE loss for the batch.
		  # tf.nce_loss automatically draws a new sample of the negative labels each
		  # time we evaluate the loss.
		  loss = tf.reduce_mean(
		      tf.nn.nce_loss(weights=nce_weights,
		                     biases=nce_biases,
		                     labels=train_labels,
		                     inputs=embed,
		                     num_sampled=num_sampled,
		                     num_classes=vocabulary_size))

		  # Construct the SGD optimizer using a learning rate of 1.0.
		  optimizer = tf.train.GradientDescentOptimizer(1.0).minimize(loss)

		  # Compute the cosine similarity between minibatch examples and all embeddings.
		  norm = tf.sqrt(tf.reduce_sum(tf.square(embeddings), 1, keep_dims=True))
		  normalized_embeddings = embeddings / norm
		  valid_embeddings = tf.nn.embedding_lookup(
		      normalized_embeddings, valid_dataset)
		  similarity = tf.matmul(
		      valid_embeddings, normalized_embeddings, transpose_b=True)

		  # Add variable initializer.
		  init = tf.global_variables_initializer()

		# Step 5: Begin training.
		num_steps = 100001

		with tf.Session(graph=graph) as session:
		  # We must initialize all variables before we use them.
		  init.run()
		  print('Initialized')

		  average_loss = 0
		  for step in xrange(num_steps):
		    batch_inputs, batch_labels = self.generate_batch(
		        batch_size, num_skips, skip_window)
		    feed_dict = {train_inputs: batch_inputs, train_labels: batch_labels}

		    # We perform one update step by evaluating the optimizer op (including it
		    # in the list of returned values for session.run()
		    _, loss_val = session.run([optimizer, loss], feed_dict=feed_dict)
		    average_loss += loss_val

		    if step % 2000 == 0:
		      if step > 0:
		        average_loss /= 2000
		      # The average loss is an estimate of the loss over the last 2000 batches.
		      print('Average loss at step ', step, ': ', average_loss)
		      average_loss = 0

		    # Note that this is expensive (~20% slowdown if computed every 500 steps)
		    '''
		    if step % 10000 == 0:
		      sim = similarity.eval()
		      for i in xrange(valid_size):
		        valid_word = self.reverse_dictionary[valid_examples[i]]
		        top_k = 8  # number of nearest neighbors
		        nearest = (-sim[i, :]).argsort()[1:top_k + 1]
		        log_str = 'Nearest to %s:' % valid_word
		        for k in xrange(top_k):
		          close_word = self.reverse_dictionary[nearest[k]]
		          log_str = '%s %s,' % (log_str, close_word)
		        print(log_str)
		    '''
		  final_embeddings = normalized_embeddings.eval()
		  self.final_embeddings = final_embeddings
		  
		  #tbh there's no point in returning the final_embeddings bc
		  #they are identical; but whatever
		  clustered_synonyms, final_embeddings, low_dim_embs = self.cluster(final_embeddings)
		  self.low_dim_embs = low_dim_embs

		  #print(self.reverse_dictionary)
		  return final_embeddings, low_dim_embs, self.reverse_dictionary, clustered_synonyms

	# the direct result of clustering the first time is
	#a KMeans object containing the labeled word vectors (in 2D space)
	#the original final_embeddings matrix, which we will likely not need but is kept for now
	#the reduced-dimension low_dim_embs matrix, which has the same rows as final_embeddings, but only two cols
	# in short, cluster() transforms final_embeddings -> low_dim_embs; and clusters low_dim_embs -> synonyms
	def cluster(self, final_embeddings):
		#reduce dimension to perform kmeans
		tsne = TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000)
		#TODO rectify this number
		cap = 12000

		#this 'flattens' the words so they can be represented as 2D vectors
		low_dim_embs = tsne.fit_transform(final_embeddings[:cap,:])

		#now we cluster those words with kmeans
		clustered_synonyms = KMeans(n_clusters=2, random_state=0, algorithm='elkan').fit(low_dim_embs)

		self.clustered_synonyms = clustered_synonyms

		return clustered_synonyms, final_embeddings, low_dim_embs

	# this should be called ONLY after already calling cluster on the original final_embeddings
	#because it returns low_dim_embs, aka nx2 dimensional matrix of word vectors
	#which we will use to extract vectors of the same label, and re-cluster
	# this is NOT a recursive method; the caller will need to check the size of the new dictionary
	#to decide when to stop calling re_cluster()
	# NOTE: the first time you call re_cluster(), reverse_dictionary will be the same reverse_dictionary
	#you get from calling train(); re_clustering afterwards, use the new_reverse_dictionary returned
	def re_cluster(self, low_dim_embs, clustered_synonyms, target_keyword, dictionary, reverse_dictionary):
		#we must assume that the reverse dictionary gives us the index
		#of the word in the embeddings matrix

		#NOTE: index-to-word is reverse_dictionary
		#      word-to-index is dictionary

		#find the keyword embedding
		index = dictionary[target_keyword]
		target_embedding = low_dim_embs[index]

		#print(target_keyword + ': ' + str(target_embedding))

		#labels is a index-to-index correspondence of each word vector's label/cluster
		labels = clustered_synonyms.labels_

		#find label of target_embedding
		target_label = labels[index]

		#find the starting index of that label in labels
		start = 0
		for i in range(len(labels)):
			if labels[i] == target_label:
				start = i
				break

		#for each index with that label number, append an embedding from the corresponding index in low_dim_embs to a new matrix
		new_embeddings = []

		#we must also build a new reverse dictionary representing the word:index pairs

		#build a new reverse dictionary to keep indices consistent with the new clustered_synonyms.labels_
		#aka this is to ensure we can still match the ith label with the ith word in new_reverse_dictionary,
		#as well as the ith row in the new_embeddings matrix
		new_reverse_dictionary = dict()
		new_dictionary = dict()
		index = 0

		to_append = low_dim_embs[start]
		word = reverse_dictionary[start]
		new_embeddings = [to_append]
		new_reverse_dictionary[index] = word
		new_dictionary[word] = index
		index += 1
		start += 1

		while start < len(labels):
			if labels[start] == target_label:
				#to_append is just a row vector representing the embedded word
				to_append = low_dim_embs[start]

				#TODO verify that this is correct
				word = reverse_dictionary[start]
				new_embeddings = np.append(new_embeddings, [to_append], axis=0)
				new_reverse_dictionary[index] = word
				new_dictionary[word] = index
				index += 1
			start += 1

		#cluster
		clustered_synonyms = KMeans(n_clusters=2, random_state=0, algorithm='elkan').fit(new_embeddings)

		return clustered_synonyms, new_embeddings, new_dictionary, new_reverse_dictionary

	def extractSynonyms(self, clustered_synonyms, target_keyword, dictionary, reverse_dictionary):
		index = dictionary[target_keyword]
		labels = clustered_synonyms.labels_

		target_label = labels[index]

		synonyms = ['']

		for i in range(len(labels)):
			if labels[i] == target_label:
				word = reverse_dictionary[i]
				synonyms.append(word)

		return synonyms


#==Load saved skipgram model==
'''
#==Code for testing clustering==
file = bz2.BZ2File('./modules/default_skipgram.pkl.bz','rb')
model = cPickle.load(file)
file.close()
reverse_dictionary = model.reverse_dictionary
dictionary = model.dictionary
final_embeddings = model.final_embeddings

print('beginning clustering')

import time
start_time = time.time()
clustered_synonyms, final_embeddings, low_dim_embs = model.cluster(final_embeddings)
print("--- %s seconds ---" % (time.time() - start_time))

print('now testing re_clustering with target_keyword=dictatorship')
target_keyword='dictatorship'
clustered_synonyms, new_embeddings, new_dictionary, new_reverse_dictionary = model.re_cluster(low_dim_embs, clustered_synonyms, target_keyword, dictionary, reverse_dictionary)

print('The new list of words')
print(new_reverse_dictionary)
'''
#==Plot clusters. Output: tsne.png==
'''
try:
	# pylint: disable=g-import-not-at-top
  	import matplotlib.pyplot as plt
  	tsne = TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000)
  	plot_only = 750
  	low_dim_embs = tsne.fit_transform(final_embeddings[:plot_only, :])
  	labels = [reverse_dictionary[i] for i in xrange(plot_only)]
  	model.plot_with_labels(low_dim_embs, labels)
except ImportError:
	print('Please install sklearn, matplotlib, and scipy to show embeddings.')
'''
