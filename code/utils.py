def merge_dicts(dicts):
	merged_dict = {}
	for dict_ in dicts:
		merged_dict = {**merged_dict, **dict_}
	return merged_dict