from core.imports import wraps, datetime

# ----------------------------------- ДЕКОРАТОРЫ (декоратор для отслеживания вызовов функций) ----------------------------

def track_usage(func_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from handlers.admin.statistics.statistics import load_statistics, save_statistics
            statistics = load_statistics()
            current_date = datetime.now().strftime('%d.%m.%Y')

            if current_date not in statistics:
                statistics[current_date] = {'users': set(), 'functions': {}}
            if 'functions' not in statistics[current_date]:
                statistics[current_date]['functions'] = {}
            if func_name not in statistics[current_date]['functions']:
                statistics[current_date]['functions'][func_name] = 0
            statistics[current_date]['functions'][func_name] += 1

            save_statistics(statistics)
            return func(*args, **kwargs)
        return wrapper
    return decorator