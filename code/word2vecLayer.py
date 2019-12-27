import requests
import json

def get_similarity(word1, word2):
	input_data = {"word1": word1, "word2": word2}
	similarity_response = requests.post("http://localhost:5005/", data = {"stringifiedData": json.dumps(input_data)})
	return float(similarity_response.json()["similarity"])

def is_similar(word1, word2, thresh = 0.75):
	input_data = {"word1": word1, "word2": word2, "thresh": thresh}
	similarity_response = requests.post("http://localhost:5005/", data = {"stringifiedData": json.dumps(input_data)})
	return (similarity_response.json()["passedThresh"] == 1)

def get_best_similarity_in(word, word_list):
	best_similarity = -1.0;
	for word2 in word_list:
		best_similarity = max(best_similarity, get_similarity(word, word2))
	return best_similarity

def has_similar_word_in(word, word_list, thresh = 0.75):
	for word2 in word_list:
		if is_similar(word, word2, thresh):
			return True
	return False