"""
Generic menu registry.

Each concrete registry (settings_menu, my_settings_menu, …) instantiates
MenuRegistry and uses its @register decorator to collect class-based menu
entries at Django startup (via AppConfig.ready → import app.menu).
"""


class MenuRegistry:
    """
    Collects menu-entry classes registered with @register and renders them
    into a filtered, sorted list of dicts on each request.

    Ordering uses a three-bucket strategy so that:
      - entries with order >= 0  appear first,  sorted ascending
      - entries with no order    appear second (stable insertion order)
      - entries with order < 0   appear last,   sorted ascending
    """

    def __init__(self):
        self._entries = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, cls):
        """Decorator — add cls to this registry and return it unchanged."""
        self._entries.append(cls)
        return cls

    # ------------------------------------------------------------------
    # Condition helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_visible(entry_obj, request):
        """Return True if the entry's condition passes."""
        condition = getattr(entry_obj, "condition", True)
        if callable(condition):
            try:
                return bool(condition(request))
            except TypeError:
                # some callables are defined as lambda self, request: …
                return bool(condition(entry_obj, request))
        return bool(condition)

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    @staticmethod
    def _sort_key(entry_obj):
        order = getattr(entry_obj, "order", None)
        if order is None:
            return (1, 0)
        if order >= 0:
            return (0, order)
        return (2, order)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_entries(self, request):
        """
        Return all registered entries that pass their condition, sorted by
        the three-bucket order strategy.  Subclasses override _build_entry
        to control the shape of each returned object.
        """
        results = []
        for cls in self._entries:
            obj = cls()
            if not self._is_visible(obj, request):
                continue
            built = self._build_entry(obj, request)
            if built is not None:
                results.append((self._sort_key(obj), built))

        results.sort(key=lambda x: x[0])
        return [entry for _, entry in results]

    def _build_entry(self, obj, request):
        """
        Convert a registered class instance into whatever structure the
        template expects.  Override in subclasses.
        """
        raise NotImplementedError
