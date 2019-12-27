import nltk
import nltk.parse.corenlp as cnlp
import nltk.parse.stanford as snlp


class QueryParser:
	CORENLP_SERVER = "http://localhost:9000"

	def __init__(self):
		self.parser = cnlp.CoreNLPParser(url = self.CORENLP_SERVER)
		self.dependency_parser = cnlp.CoreNLPDependencyParser(url = self.CORENLP_SERVER)
		self.cache = {}

	def syntactic_parse(self, query):
		if query in self.cache and "syntactic" in self.cache[query]:
			return self.cache[query]["syntactic"]
		syntactic_parse_tree = next(self.parser.parse_text(query))
		if not (query in self.cache):
			self.cache[query] = {}
		self.cache[query]["syntactic"] = syntactic_parse_tree
		return syntactic_parse_tree

	def dependency_parse(self, query):
		if query in self.cache and "dependency" in self.cache[query]:
			return self.cache[query]["dependency"]
		dependency_parse_tree = next(self.dependency_parser.parse_text(query))
		if not (query in self.cache):
			self.cache[query] = {}
		self.cache[query]["dependency"] = dependency_parse_tree
		return dependency_parse_tree