# Custom imports
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func

from configs import dify_config
from extensions.ext_database import db
from models.account import (
    Account,
    TenantAccountJoin,
    TenantAccountRole,
)
from models.dataset import Dataset, Document
from models.model import App, MessageAnnotation
from models.system_custom_info import SystemCustomInfo
from services.billing_service import BillingService
from services.enterprise.enterprise_service import EnterpriseService


# Custom models for Pydantic validation
class FeatureCustomModel(BaseModel):
    members: int = 1
    apps: int = dify_config.user_account_max_of_apps
    vector_space: int = dify_config.user_account_max_vector_space
    knowledge_rate_limit: int = dify_config.user_account_knowledge_rate_limit
    annotation_quota_limit: int = dify_config.user_account_max_annotation_quota_limit
    documents_upload_quota: int = dify_config.user_account_max_documents_upload_quota

class PlanModel(BaseModel):
    id: str
    name: str
    description: str
    price: float
    plan_expiration: int   # number of days until expiration
    features: FeatureCustomModel

# -----
class SubscriptionModel(BaseModel):
    plan: str = "sandbox"
    interval: str = ""


class BillingModel(BaseModel):
    enabled: bool = False
    subscription: SubscriptionModel = SubscriptionModel()


class EducationModel(BaseModel):
    enabled: bool = False
    activated: bool = False


class LimitationModel(BaseModel):
    size: int = 0
    limit: int = 0


class LicenseLimitationModel(BaseModel):
    """
    - enabled: whether this limit is enforced
    - size: current usage count
    - limit: maximum allowed count; 0 means unlimited
    """

    enabled: bool = Field(False, description="Whether this limit is currently active")
    size: int = Field(0, description="Number of resources already consumed")
    limit: int = Field(0, description="Maximum number of resources allowed; 0 means no limit")

    def is_available(self, required: int = 1) -> bool:
        """
        Determine whether the requested amount can be allocated.

        Returns True if:
         - this limit is not active, or
         - the limit is zero (unlimited), or
         - there is enough remaining quota.
        """
        if not self.enabled or self.limit == 0:
            return True

        return (self.limit - self.size) >= required


class LicenseStatus(StrEnum):
    NONE = "none"
    INACTIVE = "inactive"
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    LOST = "lost"


class LicenseModel(BaseModel):
    status: LicenseStatus = LicenseStatus.NONE
    expired_at: str = ""
    workspaces: LicenseLimitationModel = LicenseLimitationModel(enabled=False, size=0, limit=0)


class BrandingModel(BaseModel):
    enabled: bool = False
    application_title: str = ""
    login_page_logo: str = ""
    workspace_logo: str = ""
    favicon: str = ""


class WebAppAuthSSOModel(BaseModel):
    protocol: str = ""


class WebAppAuthModel(BaseModel):
    enabled: bool = False
    allow_sso: bool = False
    sso_config: WebAppAuthSSOModel = WebAppAuthSSOModel()
    allow_email_code_login: bool = False
    allow_email_password_login: bool = False


class FeatureModel(BaseModel):
    billing: BillingModel = BillingModel()
    education: EducationModel = EducationModel()
    members: LimitationModel = LimitationModel(size=0, limit=1)
    apps: LimitationModel = LimitationModel(size=0, limit=10)
    vector_space: LimitationModel = LimitationModel(size=0, limit=5)
    knowledge_rate_limit: int = 10
    annotation_quota_limit: LimitationModel = LimitationModel(size=0, limit=10)
    documents_upload_quota: LimitationModel = LimitationModel(size=0, limit=50)
    docs_processing: str = "standard"
    can_replace_logo: bool = False
    model_load_balancing_enabled: bool = False
    dataset_operator_enabled: bool = False
    webapp_copyright_enabled: bool = False
    workspace_members: LicenseLimitationModel = LicenseLimitationModel(enabled=False, size=0, limit=0)

    # pydantic configs
    model_config = ConfigDict(protected_namespaces=())


class KnowledgeRateLimitModel(BaseModel):
    enabled: bool = False
    limit: int = 10
    subscription_plan: str = ""


class SystemFeatureModel(BaseModel):
    sso_enforced_for_signin: bool = False
    sso_enforced_for_signin_protocol: str = ""
    enable_marketplace: bool = False
    max_plugin_package_size: int = dify_config.PLUGIN_MAX_PACKAGE_SIZE
    enable_email_code_login: bool = False
    enable_email_password_login: bool = True
    enable_social_oauth_login: bool = False
    is_allow_register: bool = False
    is_allow_create_workspace: bool = False
    is_email_setup: bool = False
    license: LicenseModel = LicenseModel()
    branding: BrandingModel = BrandingModel()
    webapp_auth: WebAppAuthModel = WebAppAuthModel()


class FeatureService:
    @classmethod
    def get_features(cls, tenant_id: str) -> FeatureModel:
        features = FeatureModel()

        cls._fulfill_params_from_env(features)

        # if dify_config.BILLING_ENABLED:
        #     cls._fulfill_params_from_billing_api(features, tenant_id)
        cls._fulfill_params_from_billing_self_host(features, tenant_id)
        
        cls._fulfill_custom(features, tenant_id)

        return features

    @classmethod
    def _fulfill_custom(cls, features: FeatureModel, tenant_id: str):
        join = (
            db.session.query(TenantAccountJoin)
            .filter(TenantAccountJoin.tenant_id == tenant_id, TenantAccountJoin.role == TenantAccountRole.OWNER.value)
            .first()
        )
        account_owner = (
            db.session.query(Account)
            .filter(Account.id == join.account_id)
            .first()
        )
        # Get id plan and plan expiration date
        id_current_plan = account_owner.id_custom_plan
        plan_expiration = account_owner.plan_expiration
        # Check if id_current_plan and plan_expiration greater than current date
        if id_current_plan and plan_expiration:
            # Make plan_expiration timezone-aware (assuming UTC)
            plan_expiration_aware = plan_expiration.replace(tzinfo=UTC)
            # Check if plan_expiration is greater than current date
            if plan_expiration_aware > datetime.now(UTC):
                # Get list of plans
                system_custom_info = db.session.query(SystemCustomInfo).filter(
                    SystemCustomInfo.name.in_(["plan"])
                ).first()
                if system_custom_info:
                    object_plans = [PlanModel.model_validate(plan) for plan in system_custom_info.value]
                    # Get plan by id_current_plan
                    plan = next((plan for plan in object_plans if plan.id == id_current_plan), None)
                    if plan:
                        # Get plan features
                        features.members.limit = plan.features.members
                        features.apps.limit = plan.features.apps
                        features.vector_space.limit = plan.features.vector_space
                        features.knowledge_rate_limit = plan.features.knowledge_rate_limit
                        features.annotation_quota_limit.limit = plan.features.annotation_quota_limit
                        features.documents_upload_quota.limit = plan.features.documents_upload_quota

        # Edit the features here
        features.apps.limit = max(features.apps.limit, account_owner.max_of_apps)
        features.vector_space.limit = max(features.vector_space.limit, account_owner.max_vector_space)
        features.annotation_quota_limit.limit = max(features.annotation_quota_limit.limit, account_owner.max_annotation_quota_limit)
        features.documents_upload_quota.limit = max(features.documents_upload_quota.limit, account_owner.max_documents_upload_quota)

    @classmethod
    def get_knowledge_rate_limit(cls, tenant_id: str):
        knowledge_rate_limit = KnowledgeRateLimitModel()
        if dify_config.BILLING_ENABLED and tenant_id:
            knowledge_rate_limit.enabled = True
            limit_info = BillingService.get_knowledge_rate_limit(tenant_id)
            knowledge_rate_limit.limit = limit_info.get("limit", 10)
            knowledge_rate_limit.subscription_plan = limit_info.get("subscription_plan", "sandbox")
        return knowledge_rate_limit
        #return 10000

    @classmethod
    def get_system_features(cls) -> SystemFeatureModel:
        system_features = SystemFeatureModel()

        cls._fulfill_system_params_from_env(system_features)

        if dify_config.ENTERPRISE_ENABLED:
            system_features.branding.enabled = True
            system_features.webapp_auth.enabled = True
            cls._fulfill_params_from_enterprise(system_features)

        if dify_config.MARKETPLACE_ENABLED:
            system_features.enable_marketplace = True

        return system_features

    @classmethod
    def _fulfill_system_params_from_env(cls, system_features: SystemFeatureModel):
        system_features.enable_email_code_login = dify_config.ENABLE_EMAIL_CODE_LOGIN
        system_features.enable_email_password_login = dify_config.ENABLE_EMAIL_PASSWORD_LOGIN
        system_features.enable_social_oauth_login = dify_config.ENABLE_SOCIAL_OAUTH_LOGIN
        system_features.is_allow_register = dify_config.ALLOW_REGISTER
        system_features.is_allow_create_workspace = dify_config.ALLOW_CREATE_WORKSPACE
        system_features.is_email_setup = dify_config.MAIL_TYPE is not None and dify_config.MAIL_TYPE != ""

    @classmethod
    def _fulfill_params_from_env(cls, features: FeatureModel):
        features.can_replace_logo = dify_config.CAN_REPLACE_LOGO
        features.model_load_balancing_enabled = dify_config.MODEL_LB_ENABLED
        features.dataset_operator_enabled = dify_config.DATASET_OPERATOR_ENABLED
        features.education.enabled = dify_config.EDUCATION_ENABLED

    @classmethod
    def _fulfill_params_from_billing_self_host(cls, features: FeatureModel, tenant_id: str):
        features.billing.enabled = True
        features.billing.subscription.plan = "sandbox"
        features.billing.subscription.interval = "month"

        features.members.size = db.session.query(func.count(TenantAccountJoin.account_id)).filter(TenantAccountJoin.tenant_id == tenant_id).scalar()
        features.apps.size = db.session.query(func.count(App.id)).filter(App.tenant_id == tenant_id).scalar()
        features.vector_space.size = db.session.query(func.count(Dataset.id)).filter(Dataset.tenant_id == tenant_id).scalar()
        features.documents_upload_quota.size = db.session.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar()

        # Get all app of the tenant, query get only column id
        apps = db.session.query(App.id).filter(App.tenant_id == tenant_id).all()
        app_ids = [app.id for app in apps]
        features.annotation_quota_limit.size = db.session.query(func.count(MessageAnnotation.id)).filter(MessageAnnotation.app_id.in_(app_ids)).scalar()

        features.docs_processing = "standard"
        features.can_replace_logo = False
        features.model_load_balancing_enabled = False

    @classmethod
    def _fulfill_params_from_billing_api(cls, features: FeatureModel, tenant_id: str):
        billing_info = BillingService.get_info(tenant_id)

        features.billing.enabled = billing_info["enabled"]
        features.billing.subscription.plan = billing_info["subscription"]["plan"]
        features.billing.subscription.interval = billing_info["subscription"]["interval"]
        features.education.activated = billing_info["subscription"].get("education", False)

        if features.billing.subscription.plan != "sandbox":
            features.webapp_copyright_enabled = True

        if "members" in billing_info:
            features.members.size = billing_info["members"]["size"]
            features.members.limit = billing_info["members"]["limit"]

        if "apps" in billing_info:
            features.apps.size = billing_info["apps"]["size"]
            features.apps.limit = billing_info["apps"]["limit"]

        if "vector_space" in billing_info:
            features.vector_space.size = billing_info["vector_space"]["size"]
            features.vector_space.limit = billing_info["vector_space"]["limit"]

        if "documents_upload_quota" in billing_info:
            features.documents_upload_quota.size = billing_info["documents_upload_quota"]["size"]
            features.documents_upload_quota.limit = billing_info["documents_upload_quota"]["limit"]

        if "annotation_quota_limit" in billing_info:
            features.annotation_quota_limit.size = billing_info["annotation_quota_limit"]["size"]
            features.annotation_quota_limit.limit = billing_info["annotation_quota_limit"]["limit"]

        if "docs_processing" in billing_info:
            features.docs_processing = billing_info["docs_processing"]

        if "can_replace_logo" in billing_info:
            features.can_replace_logo = billing_info["can_replace_logo"]

        if "model_load_balancing_enabled" in billing_info:
            features.model_load_balancing_enabled = billing_info["model_load_balancing_enabled"]

        if "knowledge_rate_limit" in billing_info:
            features.knowledge_rate_limit = billing_info["knowledge_rate_limit"]["limit"]

    @classmethod
    def _fulfill_params_from_enterprise(cls, features: SystemFeatureModel):
        enterprise_info = EnterpriseService.get_info()

        if "SSOEnforcedForSignin" in enterprise_info:
            features.sso_enforced_for_signin = enterprise_info["SSOEnforcedForSignin"]

        if "SSOEnforcedForSigninProtocol" in enterprise_info:
            features.sso_enforced_for_signin_protocol = enterprise_info["SSOEnforcedForSigninProtocol"]

        if "EnableEmailCodeLogin" in enterprise_info:
            features.enable_email_code_login = enterprise_info["EnableEmailCodeLogin"]

        if "EnableEmailPasswordLogin" in enterprise_info:
            features.enable_email_password_login = enterprise_info["EnableEmailPasswordLogin"]

        if "IsAllowRegister" in enterprise_info:
            features.is_allow_register = enterprise_info["IsAllowRegister"]

        if "IsAllowCreateWorkspace" in enterprise_info:
            features.is_allow_create_workspace = enterprise_info["IsAllowCreateWorkspace"]

        if "Branding" in enterprise_info:
            features.branding.application_title = enterprise_info["Branding"].get("applicationTitle", "")
            features.branding.login_page_logo = enterprise_info["Branding"].get("loginPageLogo", "")
            features.branding.workspace_logo = enterprise_info["Branding"].get("workspaceLogo", "")
            features.branding.favicon = enterprise_info["Branding"].get("favicon", "")

        if "WebAppAuth" in enterprise_info:
            features.webapp_auth.allow_sso = enterprise_info["WebAppAuth"].get("allowSso", False)
            features.webapp_auth.allow_email_code_login = enterprise_info["WebAppAuth"].get(
                "allowEmailCodeLogin", False
            )
            features.webapp_auth.allow_email_password_login = enterprise_info["WebAppAuth"].get(
                "allowEmailPasswordLogin", False
            )
            features.webapp_auth.sso_config.protocol = enterprise_info.get("SSOEnforcedForWebProtocol", "")

        if "License" in enterprise_info:
            license_info = enterprise_info["License"]

            if "status" in license_info:
                features.license.status = LicenseStatus(license_info.get("status", LicenseStatus.INACTIVE))

            if "expiredAt" in license_info:
                features.license.expired_at = license_info["expiredAt"]

            if "workspaces" in license_info:
                features.license.workspaces.enabled = license_info["workspaces"]["enabled"]
                features.license.workspaces.limit = license_info["workspaces"]["limit"]
                features.license.workspaces.size = license_info["workspaces"]["used"]
