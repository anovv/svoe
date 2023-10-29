from featurizer.sql.client import FeaturizerSqlClient

c = FeaturizerSqlClient()
print(c.select_all_TEST())