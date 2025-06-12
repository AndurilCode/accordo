"""Simple dependency injection framework for configuration service."""

import inspect
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class DependencyInjectionError(Exception):
    """Exception raised when dependency injection fails."""

    pass


class ServiceRegistrationError(DependencyInjectionError):
    """Exception raised when service registration fails validation."""

    pass


class ServiceRegistry:
    """Registry for managing service dependencies."""

    def __init__(self):
        """Initialize the service registry."""
        self._services: dict[type[Any], Any] = {}
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._singletons: dict[type[Any], Any] = {}

    def register_service(self, service_type: type[T], service_instance: T) -> None:
        """Register a service instance.

        Args:
            service_type: The service type/interface
            service_instance: The service instance

        Raises:
            ServiceRegistrationError: If validation fails
        """
        # Validate the registration
        self._validate_service_registration(service_type, service_instance)
        self._services[service_type] = service_instance

    def register_factory(
        self, service_type: type[T], factory_func: Callable[[], T]
    ) -> None:
        """Register a factory function for creating service instances.

        Args:
            service_type: The service type/interface
            factory_func: Factory function that creates service instances

        Raises:
            ServiceRegistrationError: If validation fails
        """
        # Validate factory function
        self._validate_factory_function(service_type, factory_func)
        self._factories[service_type] = factory_func

    def register_singleton(
        self, service_type: type[T], factory_func: Callable[[], T]
    ) -> None:
        """Register a singleton service with lazy initialization.

        Args:
            service_type: The service type/interface
            factory_func: Factory function that creates the singleton instance

        Raises:
            ServiceRegistrationError: If validation fails
        """
        # Validate factory function
        self._validate_factory_function(service_type, factory_func)
        self._factories[service_type] = factory_func
        # Mark as singleton by adding to singletons dict with None value
        self._singletons[service_type] = None

    def get_service(self, service_type: type[T]) -> T:
        """Get a service instance.

        Args:
            service_type: The service type/interface

        Returns:
            Service instance

        Raises:
            DependencyInjectionError: If service is not registered
        """
        try:
            # Check for direct service registration
            if service_type in self._services:
                return self._services[service_type]

            # Check for singleton
            if service_type in self._singletons:
                if self._singletons[service_type] is None:
                    # Lazy initialization of singleton
                    if service_type not in self._factories:
                        raise DependencyInjectionError(
                            f"No factory registered for singleton service: {service_type.__name__}"
                        )
                    try:
                        self._singletons[service_type] = self._factories[service_type]()
                    except Exception as e:
                        raise DependencyInjectionError(
                            f"Failed to create singleton instance for {service_type.__name__}: {e}"
                        ) from e
                return self._singletons[service_type]

            # Check for factory
            if service_type in self._factories:
                try:
                    return self._factories[service_type]()
                except Exception as e:
                    raise DependencyInjectionError(
                        f"Failed to create instance from factory for {service_type.__name__}: {e}"
                    ) from e

            raise DependencyInjectionError(
                f"Service not registered: {service_type.__name__}"
            )
        except Exception as e:
            # Enhanced error context
            if not isinstance(e, DependencyInjectionError):
                raise DependencyInjectionError(
                    f"Unexpected error retrieving service {service_type.__name__}: {e}"
                ) from e
            raise

    def has_service(self, service_type: type[T]) -> bool:
        """Check if a service is registered.

        Args:
            service_type: The service type/interface

        Returns:
            True if service is registered, False otherwise
        """
        return (
            service_type in self._services
            or service_type in self._factories
            or service_type in self._singletons
        )

    def validate_registration(self, service_type: type[T], implementation: Any) -> bool:
        """Validate that an implementation complies with its service interface.

        Args:
            service_type: The service type/interface
            implementation: The implementation to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            self._validate_service_registration(service_type, implementation)
            return True
        except ServiceRegistrationError:
            return False

    def get_registered_services(self) -> dict[str, str]:
        """Get a summary of all registered services.

        Returns:
            Dictionary mapping service names to registration types
        """
        services_summary = {}

        for service_type in self._services:
            services_summary[service_type.__name__] = "direct_instance"

        for service_type in self._factories:
            if service_type in self._singletons:
                services_summary[service_type.__name__] = "singleton_factory"
            else:
                services_summary[service_type.__name__] = "factory"

        return services_summary

    def clear_registry(self) -> None:
        """Clear all registered services (primarily for testing)."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()

    def _validate_service_registration(
        self, service_type: type[T], implementation: Any
    ) -> None:
        """Validate service registration.

        Args:
            service_type: The service type/interface
            implementation: The implementation to validate

        Raises:
            ServiceRegistrationError: If validation fails
        """
        if service_type is None:
            raise ServiceRegistrationError("Service type cannot be None")

        if implementation is None:
            raise ServiceRegistrationError(
                f"Service implementation cannot be None for {service_type.__name__}"
            )

        # Check if it's a Protocol (multiple ways to detect)
        is_protocol = (
            hasattr(service_type, "__protocol__")
            or hasattr(service_type, "_is_protocol")
            or getattr(service_type, "__module__", "").endswith("_protocol")
            or "Protocol" in getattr(service_type, "__name__", "")
        )

        if is_protocol:
            # For Protocol types, use structural validation instead of isinstance
            self._validate_protocol_implementation(service_type, implementation)
        else:
            # For regular types, check isinstance
            try:
                if not isinstance(implementation, service_type):
                    raise ServiceRegistrationError(
                        f"Implementation {type(implementation).__name__} is not an instance of {service_type.__name__}"
                    )
            except TypeError:
                # Fallback for protocols that can't use isinstance
                self._validate_protocol_implementation(service_type, implementation)

    def _validate_factory_function(
        self, service_type: type[T], factory_func: Callable[[], T]
    ) -> None:
        """Validate factory function.

        Args:
            service_type: The service type/interface
            factory_func: The factory function to validate

        Raises:
            ServiceRegistrationError: If validation fails
        """
        if not callable(factory_func):
            raise ServiceRegistrationError(
                f"Factory function for {service_type.__name__} must be callable"
            )

        # Check function signature
        sig = inspect.signature(factory_func)
        if len(sig.parameters) > 0:
            raise ServiceRegistrationError(
                f"Factory function for {service_type.__name__} should not require parameters"
            )

    def _validate_protocol_implementation(
        self, protocol_type: type, implementation: Any
    ) -> None:
        """Validate that implementation satisfies protocol requirements.

        Args:
            protocol_type: The protocol type
            implementation: The implementation to validate

        Raises:
            ServiceRegistrationError: If validation fails
        """
        # Get protocol methods/attributes
        if hasattr(protocol_type, "__annotations__"):
            for name, _annotation in protocol_type.__annotations__.items():
                if not hasattr(implementation, name):
                    raise ServiceRegistrationError(
                        f"Implementation {type(implementation).__name__} missing required attribute '{name}' "
                        f"from protocol {protocol_type.__name__}"
                    )

        # Check protocol methods
        for name in dir(protocol_type):
            if (
                not name.startswith("_")
                and callable(getattr(protocol_type, name, None))
                and (
                    not hasattr(implementation, name)
                    or not callable(getattr(implementation, name))
                )
            ):
                raise ServiceRegistrationError(
                    f"Implementation {type(implementation).__name__} missing required method '{name}' "
                    f"from protocol {protocol_type.__name__}"
                )


# Global service registry
_service_registry = ServiceRegistry()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry.

    Returns:
        ServiceRegistry instance
    """
    return _service_registry


def register_service(service_type: type[T], service_instance: T) -> None:
    """Register a service instance in the global registry.

    Args:
        service_type: The service type/interface
        service_instance: The service instance
    """
    _service_registry.register_service(service_type, service_instance)


def register_factory(service_type: type[T], factory_func: Callable[[], T]) -> None:
    """Register a factory function in the global registry.

    Args:
        service_type: The service type/interface
        factory_func: Factory function that creates service instances
    """
    _service_registry.register_factory(service_type, factory_func)


def register_singleton(service_type: type[T], factory_func: Callable[[], T]) -> None:
    """Register a singleton service in the global registry.

    Args:
        service_type: The service type/interface
        factory_func: Factory function that creates the singleton instance
    """
    _service_registry.register_singleton(service_type, factory_func)


def get_service(service_type: type[T]) -> T:
    """Get a service instance from the global registry.

    Args:
        service_type: The service type/interface

    Returns:
        Service instance

    Raises:
        DependencyInjectionError: If service is not registered
    """
    return _service_registry.get_service(service_type)


def has_service(service_type: type[T]) -> bool:
    """Check if a service is registered in the global registry.

    Args:
        service_type: The service type/interface

    Returns:
        True if service is registered, False otherwise
    """
    return _service_registry.has_service(service_type)


def clear_registry() -> None:
    """Clear all registered services (primarily for testing)."""
    _service_registry.clear_registry()


# Dependency injection decorators
def inject_service(service_type: type[T]) -> Callable[[Callable], Callable]:
    """Decorator to inject a service into a function or method.

    Args:
        service_type: The service type to inject

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Inject the service as the first argument
            service = get_service(service_type)
            return func(service, *args, **kwargs)

        return wrapper

    return decorator


def inject_config_service(func: Callable) -> Callable:
    """Convenience decorator to inject the configuration service.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    def wrapper(*args, **kwargs):
        from .config_service import get_configuration_service

        config_service = get_configuration_service()
        return func(config_service, *args, **kwargs)

    return wrapper
