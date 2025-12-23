import os
import json

# Initialize data structures
step_durations = {}
step_input_tokens = {}
step_output_tokens = {}

all_input_tokens = []
all_output_tokens = []
all_total_times = []

for log_file in os.listdir("logs"):
    if log_file.endswith('.json'):
        with open(os.path.join("logs", log_file), "r") as f:
            data = json.load(f)
        
        # Collect per step
        for step in data['steps']:
            node = step['node']
            duration = step['duration_s']
            input_tokens = step['input_tokens']
            output_tokens = step['output_tokens']
            
            if node not in step_durations:
                step_durations[node] = []
                step_input_tokens[node] = []
                step_output_tokens[node] = []
            step_durations[node].append(duration)
            step_input_tokens[node].append(input_tokens)
            step_output_tokens[node].append(output_tokens)
        
        # Collect totals
        all_total_times.append(data['totals']['total_duration_s'])
        all_input_tokens.append(data['totals']['total_input_tokens'])
        all_output_tokens.append(data['totals']['total_output_tokens'])


# Compute averages per step
avg_durations_per_step = {node: sum(durs) / len(durs) for node, durs in step_durations.items()}
avg_input_tokens_per_step = {node: sum(tokens) / len(tokens) for node, tokens in step_input_tokens.items()}
avg_output_tokens_per_step = {node: sum(tokens) / len(tokens) for node, tokens in step_output_tokens.items()}

# Overall averages
avg_input_tokens = sum(all_input_tokens) / len(all_input_tokens) if all_input_tokens else 0
avg_output_tokens = sum(all_output_tokens) / len(all_output_tokens) if all_output_tokens else 0
avg_total_time = sum(all_total_times) / len(all_total_times) if all_total_times else 0

# Max and min inference time
max_duration = max(all_total_times) if all_total_times else 0
min_duration = min(all_total_times) if all_total_times else 0
# Print results
print("Average inference time per step:")
for node, avg in avg_durations_per_step.items():
    print(f"{node}: {avg:.4f}s")

print("\nAverage input tokens per step:")
for node, avg in avg_input_tokens_per_step.items():
    print(f"{node}: {avg:.2f}")

print("\nAverage output tokens per step:")
for node, avg in avg_output_tokens_per_step.items():
    print(f"{node}: {avg:.2f}")

print(f"\nOverall average input tokens: {avg_input_tokens:.2f}")
print(f"Overall average output tokens: {avg_output_tokens:.2f}")
print(f"Overall average total time: {avg_total_time:.4f}s")
print(f"Max inference time: {max_duration:.4f}s")
print(f"Min inference time: {min_duration:.4f}s")