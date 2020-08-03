import logging

from pandas import DataFrame, Series

from .abstract import AbstractFeatureGenerator
from ..feature_metadata import FeatureMetadata

logger = logging.getLogger(__name__)


class IdentityFeatureGenerator(AbstractFeatureGenerator):
    def _fit_transform(self, X: DataFrame, y: Series = None, feature_metadata_in: FeatureMetadata = None) -> (DataFrame, dict):
        X_out = self._transform(X)
        return X_out, None

    def _transform(self, X):
        return self._generate_features_identity(X)

    def _infer_features_in_from_metadata(self, X, y=None, feature_metadata_in: FeatureMetadata = None) -> list:
        identity_features = []
        invalid_raw_types = {'object', 'datetime'}
        features = feature_metadata_in.get_features()
        for feature in features:
            feature_type_raw = feature_metadata_in.get_feature_type_raw(feature)
            if feature_type_raw not in invalid_raw_types:
                identity_features.append(feature)
        return identity_features

    def _generate_features_identity(self, X: DataFrame):
        return X[self.features_in]
