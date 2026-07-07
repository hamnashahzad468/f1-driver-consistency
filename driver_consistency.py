import fastf1
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

# Setup cache
os.makedirs('f1_cache', exist_ok=True)
fastf1.Cache.enable_cache('f1_cache')

# 2026 races
races = [
    'Australia', 'China', 'Japan',
    'Miami', 'Canada', 'Monaco',
    'Spain', 'Austria'
]

# Top drivers to analyse
top_drivers = ['RUS', 'ANT', 'LEC', 'HAM', 'VER', 'PIA', 'NOR', 'SAI']

print("Loading data... this may take a few minutes")

all_data = []

for race in races:
    try:
        session = fastf1.get_session(2026, race, 'R')
        session.load(telemetry=False, weather=False, messages=False)

        for driver in top_drivers:
            try:
                laps = session.laps.pick_drivers(driver).copy()
                laps['LapTimeSec'] = laps['LapTime'].dt.total_seconds()

                # Clean laps only
                clean = laps[laps['LapTimeSec'] < laps['LapTimeSec'].median() * 1.1]

                if len(clean) < 5:
                    continue

                # Consistency metric — coefficient of variation (lower = more consistent)
                mean_lap = clean['LapTimeSec'].mean()
                std_lap = clean['LapTimeSec'].std()
                cv = (std_lap / mean_lap) * 100

                # Finish status
                result = session.results[session.results['Abbreviation'] == driver]
                finished = 1 if not result.empty and pd.to_numeric(
                    result['Position'].values[0], errors='coerce') <= 20 else 0

                all_data.append({
                    'Driver': driver,
                    'Race': race,
                    'MeanLap': mean_lap,
                    'StdLap': std_lap,
                    'CV': cv,
                    'Finished': finished,
                    'LapCount': len(clean)
                })

            except Exception as e:
                continue

        print(f"Loaded {race}")

    except Exception as e:
        print(f"Skipped {race}: {e}")

# Create dataframe
df = pd.DataFrame(all_data)

# Aggregate by driver
summary = df.groupby('Driver').agg(
    avg_cv=('CV', 'mean'),
    avg_std=('StdLap', 'mean'),
    finish_rate=('Finished', 'mean'),
    races=('Race', 'count')
).reset_index()

summary = summary[summary['races'] >= 3]

# Consistency score (0-100)
# Lower CV = more consistent = higher score
max_cv = summary['avg_cv'].max()
min_cv = summary['avg_cv'].min()
summary['consistency_score'] = 100 - (
    (summary['avg_cv'] - min_cv) / (max_cv - min_cv) * 100)

# Finish rate score (0-100)
summary['finish_score'] = summary['finish_rate'] * 100

# Combined rating (60% consistency + 40% finish rate)
summary['overall_rating'] = (
    summary['consistency_score'] * 0.6 +
    summary['finish_score'] * 0.4
)

summary = summary.sort_values('overall_rating', ascending=False)

# --- Plotting ---
fig, axes = plt.subplots(1, 3, figsize=(18, 7))
fig.suptitle('F1 2026 Driver Consistency Rating System',
             fontsize=14, fontweight='bold')

colors = plt.cm.RdYlGn(
    np.linspace(0.2, 0.9, len(summary)))[::-1]

# --- Plot 1: Overall Rating ---
ax1 = axes[0]
bars = ax1.barh(summary['Driver'], summary['overall_rating'],
                color=colors, edgecolor='none', height=0.6)
ax1.set_xlabel('Overall Rating (0-100)', fontsize=10)
ax1.set_title('Overall Consistency Rating\n(60% Lap Consistency + 40% Finish Rate)',
              fontsize=10)
ax1.set_xlim(0, 100)
ax1.grid(True, alpha=0.3, axis='x')
ax1.invert_yaxis()

for bar, val in zip(bars, summary['overall_rating']):
    ax1.text(val + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val:.1f}', va='center', fontsize=9, color='white')

# --- Plot 2: Lap Time Consistency ---
ax2 = axes[1]
bars2 = ax2.barh(summary['Driver'], summary['consistency_score'],
                 color=colors, edgecolor='none', height=0.6)
ax2.set_xlabel('Consistency Score (0-100)', fontsize=10)
ax2.set_title('Lap Time Consistency Score\n(Based on Coefficient of Variation)',
              fontsize=10)
ax2.set_xlim(0, 100)
ax2.grid(True, alpha=0.3, axis='x')
ax2.invert_yaxis()

for bar, val in zip(bars2, summary['consistency_score']):
    ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val:.1f}', va='center', fontsize=9, color='white')

# --- Plot 3: Finish Rate ---
ax3 = axes[2]
bars3 = ax3.barh(summary['Driver'], summary['finish_score'],
                 color=colors, edgecolor='none', height=0.6)
ax3.set_xlabel('Finish Rate (%)', fontsize=10)
ax3.set_title('Race Finish Rate\n(% of races finished)',
              fontsize=10)
ax3.set_xlim(0, 100)
ax3.grid(True, alpha=0.3, axis='x')
ax3.invert_yaxis()

for bar, val in zip(bars3, summary['finish_score']):
    ax3.text(val + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val:.0f}%', va='center', fontsize=9, color='white')

plt.tight_layout()
plt.savefig('driver_consistency.png', dpi=150, bbox_inches='tight')
plt.show()

print("\n2026 Driver Consistency Rankings:")
print(summary[['Driver', 'overall_rating', 'consistency_score',
               'finish_score', 'races']].to_string(index=False))
