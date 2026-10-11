"""Воспроизводимые учебные расчёты. Все данные условные.
Запуск: python3 practice.py. Использует только стандартную библиотеку.
"""
from decimal import Decimal, ROUND_HALF_UP
from math import sqrt
from random import Random
from statistics import mean, stdev
import json
from pathlib import Path


def npv(rate, flows):
    if rate <= -1:
        raise ValueError('Ставка должна быть больше -100%')
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))


def posterior_positive(prior, sensitivity, false_positive):
    numerator = prior * sensitivity
    denominator = numerator + (1 - prior) * false_positive
    if denominator == 0:
        raise ValueError('Сигнал имеет нулевую вероятность')
    return numerator / denominator


def cash_need(initial, net_flows, reserve=0):
    balance = initial
    balances = []
    for flow in net_flows:
        balance += flow
        balances.append(balance)
    return max(0, reserve - min([initial] + balances)), balances


def linear_regression(x, y):
    if len(x) != len(y) or len(x) < 2:
        raise ValueError('Нужны одинаковые наборы минимум из двух наблюдений')
    mx, my = mean(x), mean(y)
    denominator = sum((v - mx) ** 2 for v in x)
    if denominator == 0:
        raise ValueError('Признак не меняется: наклон не идентифицирован')
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y)) / denominator
    return my - slope * mx, slope


def contract_payments(events, rates):
    """event_id идентифицирует одно утверждённое событие.
    Повторное событие пропускается только при совпадающем содержимом.
    Для реальной системы добавьте даты тарифа, права доступа и первичные документы.
    """
    seen = {}
    results = []
    for event in events:
        identifier = event['event_id']
        payload = tuple(sorted((key, str(value)) for key, value in event.items() if key != 'event_id'))
        if identifier in seen:
            if seen[identifier] != payload:
                raise ValueError(f'Конфликт содержимого события {identifier}')
            continue
        if event['work_code'] not in rates:
            raise ValueError('Нет утверждённого тарифа')
        quantity = Decimal(str(event['quantity']))
        rate = Decimal(str(rates[event['work_code']]))
        if quantity < 0 or rate < 0:
            raise ValueError('Отрицательный объём или тариф')
        amount = (quantity * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        results.append({'event_id': identifier, 'amount': str(amount)})
        seen[identifier] = payload
    return results


def quantile(sorted_values, p):
    position = p * (len(sorted_values) - 1)
    lower = int(position)
    fraction = position - lower
    if lower + 1 == len(sorted_values):
        return sorted_values[lower]
    return sorted_values[lower] * (1 - fraction) + sorted_values[lower + 1] * fraction


def simulate_margin(n=20000, seed=2026):
    """Условные распределения, не калибровка реального хозяйства.
    Цена и урожайность независимы только в данном учебном сценарии.
    Треугольные распределения задают границы, моду и асимметрию.
    """
    rng = Random(seed)
    margins = []
    for _ in range(n):
        price = rng.triangular(5.0, 8.0, 6.5)
        output = rng.triangular(1700.0, 3800.0, 3000.0)
        margins.append((price - 1.2) * output - 14000)
    ordered = sorted(margins)
    return {
        'n': n, 'seed': seed,
        'mean_margin': mean(margins),
        'sd_margin': stdev(margins),
        'probability_negative': sum(v < 0 for v in margins) / n,
        'p05': quantile(ordered, .05),
        'p50': quantile(ordered, .5),
        'p95': quantile(ordered, .95),
    }, margins


def run():
    liquidity, balances = cash_need(100000, [-80000, -70000, 200000], 20000)
    alpha, beta = linear_regression([1, 2, 3, 4], [3, 5, 7, 9])
    payments = contract_payments([
        {'event_id': 'E-001', 'work_code': 'W01', 'quantity': '2.5'},
        {'event_id': 'E-001', 'work_code': 'W01', 'quantity': '2.5'},
        {'event_id': 'E-002', 'work_code': 'W01', 'quantity': '2.5'},
    ], {'W01': '100.52'})
    simulation, _ = simulate_margin()
    results = {
        'npv_machine_ch20': npv(.15, [-150000] + [60000] * 5),
        'npv_exercise_ch20': npv(.10, [-100000, 40000, 40000, 60000]),
        'npv_exam3': npv(.12, [-200000, 70000, 70000, 70000, 100000]),
        'posterior_flag_ch4': posterior_positive(.01, .90, .05),
        'credit_line_with_reserve': liquidity,
        'unfinanced_balances': balances,
        'regression': {'alpha': alpha, 'beta': beta},
        'contract_payments': payments,
        'contract_total': str(sum(Decimal(x['amount']) for x in payments)),
        'monte_carlo': simulation,
    }
    assert abs(results['npv_machine_ch20'] - 51129.305880646) < 1e-6
    assert liquidity == 70000
    assert (alpha, beta) == (1, 2)
    assert results['contract_total'] == '502.60'
    # Проверка конфликта и отсутствующего тарифа, а не только штатного случая.
    try:
        contract_payments([
            {'event_id': 'X', 'work_code': 'W01', 'quantity': '1'},
            {'event_id': 'X', 'work_code': 'W01', 'quantity': '2'},
        ], {'W01': '100.52'})
    except ValueError:
        pass
    else:
        raise AssertionError('Не обнаружен конфликт события')
    destination = Path(__file__).with_name('verified_results.json')
    destination.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


if __name__ == '__main__':
    run()
