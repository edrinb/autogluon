import copy
import logging

from pandas import DataFrame, Series

from ..types import get_type_map_raw, get_type_group_map_special
from ..feature_metadata import FeatureMetadata
from ...utils.savers import save_pkl

logger = logging.getLogger(__name__)


# TODO: Add documentation
# TODO: Add unit tests
class AbstractFeatureGenerator:
    def __init__(self, features_in: list = None, feature_metadata_in: FeatureMetadata = None, name_prefix: str = None, name_suffix: str = None):
        # TODO: Add post_generators
        self._is_fit = False  # Whether the feature generator has been fit
        self.feature_metadata_in: FeatureMetadata = feature_metadata_in  # FeatureMetadata object based on the original input features.
        self.feature_metadata: FeatureMetadata = None  # FeatureMetadata object based on the processed features. Pass to models to enable advanced functionality.
        self.features_in = features_in  # Original features to use as input to feature generation
        self.features_out = None  # Final list of features after transformation
        self.name_prefix = name_prefix  # Prefix added to all output feature names
        self.name_suffix = name_suffix  # Suffix added to all output feature names

        self._is_updated_name = False  # If feature names have been altered by name_prefix or name_suffix

    def fit(self, X: DataFrame, **kwargs):
        self.fit_transform(X, **kwargs)

    def fit_transform(self, X: DataFrame, y: Series = None, feature_metadata_in: FeatureMetadata = None, **kwargs) -> DataFrame:
        if self._is_fit:
            raise AssertionError('FeatureGenerator is already fit.')
        if self.feature_metadata_in is None:
            self.feature_metadata_in = feature_metadata_in
        elif feature_metadata_in is not None:
            logger.warning('Warning: feature_metadata_in passed as input to fit_transform, but self.feature_metadata_in was already set. Ignoring feature_metadata_in.')
        if self.feature_metadata_in is None:
            self.feature_metadata_in = self._infer_feature_metadata_in(X=X, y=y)
        if self.features_in is None:
            self.features_in = self._infer_features_in(X, y=y)
        self.feature_metadata_in = self.feature_metadata_in.keep_features(features=self.features_in)
        X_out, type_family_groups_special = self._fit_transform(X[self.features_in], y=y, **kwargs)
        X_out, type_family_groups_special = self._update_feature_names(X_out, type_family_groups_special)
        self.features_out = list(X_out.columns)
        type_map_raw = get_type_map_raw(X_out)
        self.feature_metadata = FeatureMetadata(type_map_raw=type_map_raw, type_group_map_special=type_family_groups_special)
        self._is_fit = True
        return X_out

    def transform(self, X: DataFrame) -> DataFrame:
        if not self._is_fit:
            raise AssertionError('FeatureGenerator is not fit.')
        X_out = self._transform(X[self.features_in])
        if self._is_updated_name:
            X_out.columns = self.features_out
        return X_out

    # TODO: feature_metadata_in as parameter?
    def _fit_transform(self, X: DataFrame, **kwargs) -> (DataFrame, dict):
        raise NotImplementedError

    def _transform(self, X: DataFrame) -> DataFrame:
        raise NotImplementedError

    # TODO: Find way to increase flexibility here, possibly through init args
    def _infer_features_in(self, X: DataFrame, y: Series = None) -> list:
        return list(X.columns)

    @staticmethod
    def _infer_feature_metadata_in(X: DataFrame, y: Series = None) -> FeatureMetadata:
        type_map_raw = get_type_map_raw(X)
        type_group_map_special = get_type_group_map_special(X)
        return FeatureMetadata(type_map_raw=type_map_raw, type_group_map_special=type_group_map_special)

    def _update_feature_names(self, X: DataFrame, type_family_groups: dict) -> (DataFrame, dict):
        X_columns_orig = list(X.columns)
        if self.name_prefix:
            X.columns = [self.name_prefix + column for column in X.columns]
            if type_family_groups:
                for type in type_family_groups:
                    type_family_groups[type] = [self.name_prefix + feature for feature in type_family_groups[type]]
        if self.name_suffix:
            X.columns = [column + self.name_suffix for column in X.columns]
            if type_family_groups:
                for type in type_family_groups:
                    type_family_groups[type] = [feature + self.name_suffix for feature in type_family_groups[type]]
        if X_columns_orig != list(X.columns):
            self._is_updated_name = True
        return X, type_family_groups

    def _get_feature_metadata_full(self):
        feature_metadata_full = copy.deepcopy(self.feature_metadata.type_group_map_special)

        for key_raw in self.feature_metadata.type_group_map_raw:
            values = self.feature_metadata.type_group_map_raw[key_raw]
            for key_special in self.feature_metadata.type_group_map_special:
                values = [value for value in values if value not in self.feature_metadata.type_group_map_special[key_special]]
            if values:
                feature_metadata_full[key_raw] += values

        return feature_metadata_full

    def print_feature_metadata_info(self):
        logger.log(20, 'Processed Features (special dtypes):')
        for key, val in self.feature_metadata.type_group_map_special.items():
            if val: logger.log(20, '\t%s features: %s' % (key, len(val)))
        logger.log(20, 'Processed Features (raw dtypes):')
        for key, val in self.feature_metadata.type_group_map_raw.items():
            if val: logger.log(20, '\t%s features: %s' % (key, len(val)))
        logger.log(20, 'Processed Features:')
        for key, val in self._get_feature_metadata_full().items():
            if val: logger.log(20, '\t%s features: %s' % (key, len(val)))

    def save(self, path):
        save_pkl.save(path=path, object=self)
