from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum


# Enums for various status and role types
class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    MONITORING = "monitoring"


class PaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    EXPIRED = "expired"
    FAILED = "failed"


class PaymentMethod(str, Enum):
    QRIS = "qris"
    VIRTUAL_ACCOUNT = "virtual_account"
    BANK_TRANSFER = "bank_transfer"


class DeviceStatus(str, Enum):
    ACTIVE = "active"
    DOWN = "down"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DeviceType(str, Enum):
    OLT = "olt"
    ODC = "odc"
    ODP = "odp"
    ONU = "onu"
    MIKROTIK = "mikrotik"


class ConnectionType(str, Enum):
    PPPOE = "pppoe"
    HOTSPOT = "hotspot"


class AlarmSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    INFO = "info"


class NotificationType(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


# User and Authentication Models
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, max_length=50)
    email: str = Field(unique=True, max_length=255)
    password_hash: str = Field(max_length=255)
    full_name: str = Field(max_length=100)
    role: UserRole = Field(default=UserRole.MONITORING)
    is_active: bool = Field(default=True)
    last_login: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    activity_logs: List["ActivityLog"] = Relationship(back_populates="user")
    created_customers: List["Customer"] = Relationship(
        back_populates="created_by", sa_relationship_kwargs={"foreign_keys": "[Customer.created_by_id]"}
    )


class JWTToken(SQLModel, table=True):
    __tablename__ = "jwt_tokens"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    token_hash: str = Field(max_length=255)
    expires_at: datetime
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Customer and Billing Models
class Customer(SQLModel, table=True):
    __tablename__ = "customers"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(unique=True, max_length=20)
    name: str = Field(max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: str = Field(max_length=500)
    connection_type: ConnectionType
    is_active: bool = Field(default=True)
    created_by_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    created_by: User = Relationship(
        back_populates="created_customers", sa_relationship_kwargs={"foreign_keys": "[Customer.created_by_id]"}
    )
    subscriptions: List["CustomerSubscription"] = Relationship(back_populates="customer")
    payments: List["Payment"] = Relationship(back_populates="customer")
    pppoe_sessions: List["PPPoESession"] = Relationship(back_populates="customer")
    hotspot_sessions: List["HotspotSession"] = Relationship(back_populates="customer")


class InternetPackage(SQLModel, table=True):
    __tablename__ = "internet_packages"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    connection_type: ConnectionType
    bandwidth_up: int = Field(description="Upload bandwidth in Mbps")
    bandwidth_down: int = Field(description="Download bandwidth in Mbps")
    price: Decimal = Field(max_digits=10, decimal_places=2)
    validity_days: int = Field(default=30)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    subscriptions: List["CustomerSubscription"] = Relationship(back_populates="package")


class CustomerSubscription(SQLModel, table=True):
    __tablename__ = "customer_subscriptions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customers.id")
    package_id: int = Field(foreign_key="internet_packages.id")
    start_date: datetime
    end_date: datetime
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    customer: Customer = Relationship(back_populates="subscriptions")
    package: InternetPackage = Relationship(back_populates="subscriptions")
    invoices: List["Invoice"] = Relationship(back_populates="subscription")


# Payment and Xendit Integration Models
class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_number: str = Field(unique=True, max_length=50)
    subscription_id: int = Field(foreign_key="customer_subscriptions.id")
    xendit_invoice_id: Optional[str] = Field(default=None, max_length=100)
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    due_date: datetime
    issued_date: datetime = Field(default_factory=datetime.utcnow)
    paid_date: Optional[datetime] = Field(default=None)
    xendit_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    subscription: CustomerSubscription = Relationship(back_populates="invoices")
    payments: List["Payment"] = Relationship(back_populates="invoice")


class Payment(SQLModel, table=True):
    __tablename__ = "payments"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    payment_id: str = Field(unique=True, max_length=100)
    customer_id: int = Field(foreign_key="customers.id")
    invoice_id: int = Field(foreign_key="invoices.id")
    xendit_payment_id: Optional[str] = Field(default=None, max_length=100)
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    payment_method: PaymentMethod
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    payment_date: Optional[datetime] = Field(default=None)
    xendit_webhook_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    customer: Customer = Relationship(back_populates="payments")
    invoice: Invoice = Relationship(back_populates="payments")


# Network Device Models
class NetworkDevice(SQLModel, table=True):
    __tablename__ = "network_devices"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    device_type: DeviceType
    ip_address: str = Field(max_length=45)
    mac_address: Optional[str] = Field(default=None, max_length=17)
    location: str = Field(max_length=200)
    latitude: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=8)
    longitude: Optional[Decimal] = Field(default=None, max_digits=11, decimal_places=8)
    status: DeviceStatus = Field(default=DeviceStatus.ACTIVE)
    parent_device_id: Optional[int] = Field(default=None, foreign_key="network_devices.id")
    snmp_community: Optional[str] = Field(default=None, max_length=50)
    snmp_port: int = Field(default=161)
    api_username: Optional[str] = Field(default=None, max_length=50)
    api_password: Optional[str] = Field(default=None, max_length=100)
    api_port: Optional[int] = Field(default=None)
    firmware_version: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    last_seen: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    child_devices: List["NetworkDevice"] = Relationship(
        back_populates="parent_device", sa_relationship_kwargs={"remote_side": "[NetworkDevice.id]"}
    )
    parent_device: Optional["NetworkDevice"] = Relationship(
        back_populates="child_devices", sa_relationship_kwargs={"remote_side": "[NetworkDevice.id]"}
    )
    device_connections: List["DeviceConnection"] = Relationship(
        back_populates="from_device", sa_relationship_kwargs={"foreign_keys": "[DeviceConnection.from_device_id]"}
    )
    incoming_connections: List["DeviceConnection"] = Relationship(
        back_populates="to_device", sa_relationship_kwargs={"foreign_keys": "[DeviceConnection.to_device_id]"}
    )
    traffic_monitors: List["TrafficMonitor"] = Relationship(back_populates="device")
    device_alarms: List["DeviceAlarm"] = Relationship(back_populates="device")
    pppoe_sessions: List["PPPoESession"] = Relationship(back_populates="device")


class DeviceConnection(SQLModel, table=True):
    __tablename__ = "device_connections"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    from_device_id: int = Field(foreign_key="network_devices.id")
    to_device_id: int = Field(foreign_key="network_devices.id")
    connection_type: str = Field(max_length=50)
    port_from: Optional[str] = Field(default=None, max_length=20)
    port_to: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    from_device: NetworkDevice = Relationship(
        back_populates="device_connections",
        sa_relationship_kwargs={"foreign_keys": "[DeviceConnection.from_device_id]"},
    )
    to_device: NetworkDevice = Relationship(
        back_populates="incoming_connections",
        sa_relationship_kwargs={"foreign_keys": "[DeviceConnection.to_device_id]"},
    )


# Session Management Models
class PPPoESession(SQLModel, table=True):
    __tablename__ = "pppoe_sessions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100)
    customer_id: int = Field(foreign_key="customers.id")
    device_id: int = Field(foreign_key="network_devices.id")
    session_id: str = Field(max_length=100)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    mac_address: Optional[str] = Field(default=None, max_length=17)
    uptime: Optional[int] = Field(default=None, description="Session uptime in seconds")
    bytes_in: Optional[int] = Field(default=None)
    bytes_out: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(default=None)
    last_update: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    customer: Customer = Relationship(back_populates="pppoe_sessions")
    device: NetworkDevice = Relationship(back_populates="pppoe_sessions")


class HotspotSession(SQLModel, table=True):
    __tablename__ = "hotspot_sessions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100)
    customer_id: int = Field(foreign_key="customers.id")
    mac_address: str = Field(max_length=17)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    uptime: Optional[int] = Field(default=None, description="Session uptime in seconds")
    bytes_in: Optional[int] = Field(default=None)
    bytes_out: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(default=None)
    last_update: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    customer: Customer = Relationship(back_populates="hotspot_sessions")


# Monitoring and Traffic Models
class TrafficMonitor(SQLModel, table=True):
    __tablename__ = "traffic_monitors"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="network_devices.id")
    interface_name: str = Field(max_length=50)
    bytes_in: int = Field(default=0)
    bytes_out: int = Field(default=0)
    packets_in: int = Field(default=0)
    packets_out: int = Field(default=0)
    errors_in: int = Field(default=0)
    errors_out: int = Field(default=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    device: NetworkDevice = Relationship(back_populates="traffic_monitors")


class DeviceAlarm(SQLModel, table=True):
    __tablename__ = "device_alarms"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="network_devices.id")
    alarm_type: str = Field(max_length=50)
    severity: AlarmSeverity
    message: str = Field(max_length=500)
    is_acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = Field(default=None, max_length=100)
    acknowledged_at: Optional[datetime] = Field(default=None)
    resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    device: NetworkDevice = Relationship(back_populates="device_alarms")


# System Logging Models
class ActivityLog(SQLModel, table=True):
    __tablename__ = "activity_logs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    action: str = Field(max_length=100)
    resource_type: str = Field(max_length=50)
    resource_id: Optional[str] = Field(default=None, max_length=100)
    description: str = Field(max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    additional_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="activity_logs")


class SystemLog(SQLModel, table=True):
    __tablename__ = "system_logs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    level: str = Field(max_length=20)
    source: str = Field(max_length=100)
    message: str = Field(max_length=1000)
    error_details: Optional[str] = Field(default=None, max_length=2000)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Notification Models
class NotificationTemplate(SQLModel, table=True):
    __tablename__ = "notification_templates"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    notification_type: NotificationType
    subject: Optional[str] = Field(default=None, max_length=200)
    template: str = Field(max_length=2000)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationQueue(SQLModel, table=True):
    __tablename__ = "notification_queue"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    notification_type: NotificationType
    recipient: str = Field(max_length=255)
    subject: Optional[str] = Field(default=None, max_length=200)
    message: str = Field(max_length=2000)
    priority: int = Field(default=5)
    status: str = Field(default="pending", max_length=20)
    attempts: int = Field(default=0)
    last_attempt: Optional[datetime] = Field(default=None)
    scheduled_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Webhook Models
class WebhookLog(SQLModel, table=True):
    __tablename__ = "webhook_logs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50)
    event_type: str = Field(max_length=100)
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    headers: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    processed: bool = Field(default=False)
    processing_result: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)


# Configuration Models
class SystemConfiguration(SQLModel, table=True):
    __tablename__ = "system_configurations"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, max_length=100)
    value: str = Field(max_length=2000)
    description: Optional[str] = Field(default=None, max_length=500)
    is_encrypted: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Non-persistent schemas for validation and API
class UserCreate(SQLModel, table=False):
    username: str = Field(max_length=50)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(max_length=100)
    role: UserRole = Field(default=UserRole.MONITORING)


class UserUpdate(SQLModel, table=False):
    username: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[UserRole] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class CustomerCreate(SQLModel, table=False):
    customer_code: str = Field(max_length=20)
    name: str = Field(max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: str = Field(max_length=500)
    connection_type: ConnectionType


class NetworkDeviceCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    device_type: DeviceType
    ip_address: str = Field(max_length=45)
    mac_address: Optional[str] = Field(default=None, max_length=17)
    location: str = Field(max_length=200)
    latitude: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=8)
    longitude: Optional[Decimal] = Field(default=None, max_digits=11, decimal_places=8)
    parent_device_id: Optional[int] = Field(default=None)
    snmp_community: Optional[str] = Field(default=None, max_length=50)
    snmp_port: int = Field(default=161)
    api_username: Optional[str] = Field(default=None, max_length=50)
    api_password: Optional[str] = Field(default=None, max_length=100)
    api_port: Optional[int] = Field(default=None)


class InternetPackageCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    connection_type: ConnectionType
    bandwidth_up: int
    bandwidth_down: int
    price: Decimal = Field(max_digits=10, decimal_places=2)
    validity_days: int = Field(default=30)


class PaymentWebhook(SQLModel, table=False):
    payment_id: str
    status: PaymentStatus
    amount: Decimal
    payment_method: PaymentMethod
    webhook_data: Dict[str, Any] = Field(default={})


class DeviceTopologyResponse(SQLModel, table=False):
    device: NetworkDevice
    children: List["DeviceTopologyResponse"] = Field(default=[])
    connections: List[DeviceConnection] = Field(default=[])


class DashboardStats(SQLModel, table=False):
    connected_devices: int = Field(default=0)
    active_pppoe_users: int = Field(default=0)
    active_hotspot_users: int = Field(default=0)
    pending_payments: int = Field(default=0)
    critical_alarms: int = Field(default=0)
    total_revenue: Decimal = Field(default=Decimal("0"), max_digits=15, decimal_places=2)
