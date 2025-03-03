# __quick_start_begin__
import gymnasium as gym
import numpy as np
import torch

from ray.rllib.algorithms.ppo import PPOConfig


# Define your problem using python and Farama-Foundation's gymnasium API:
class SimpleCorridor(gym.Env):
    """Corridor in which an agent must learn to move right to reach the exit.

    ---------------------
    | S | 1 | 2 | 3 | G |   S=start; G=goal; corridor_length=5
    ---------------------

    Possible actions to chose from are: 0=left; 1=right
    Observations are floats indicating the current field index, e.g. 0.0 for
    starting position, 1.0 for the field next to the starting position, etc..
    Rewards are -0.1 for all steps, except when reaching the goal (+1.0).
    """

    def __init__(self, config):
        self.end_pos = config["corridor_length"]
        self.cur_pos = 0.0
        self.action_space = gym.spaces.Discrete(2)  # left and right
        self.observation_space = gym.spaces.Box(0.0, self.end_pos, (1,), np.float32)

    def reset(self, *, seed=None, options=None):
        """Resets the episode.

        Returns:
           Initial observation of the new episode and an info dict.
        """
        self.cur_pos = 0.0
        # Return initial observation.
        return np.array([self.cur_pos], np.float32), {}

    def step(self, action):
        """Takes a single step in the episode given `action`.

        Returns:
            New observation, reward, terminated-flag, truncated-flag, info-dict (empty).
        """
        # Walk left.
        if action == 0 and self.cur_pos > 0:
            self.cur_pos -= 1
        # Walk right.
        elif action == 1:
            self.cur_pos += 1
        # Set `terminated` flag when end of corridor (goal) reached.
        terminated = self.cur_pos >= self.end_pos
        truncated = False
        # +1 when goal reached, otherwise -1.
        reward = 1.0 if terminated else -0.1
        return np.array([self.cur_pos], np.float32), reward, terminated, truncated, {}


# Create an RLlib Algorithm instance from a PPOConfig object.
config = (
    PPOConfig().environment(
        # Env class to use (here: our gym.Env sub-class from above).
        SimpleCorridor,
        # Config dict to be passed to our custom env's constructor.
        # Use corridor with 20 fields (including S and G).
        env_config={"corridor_length": 20},
    )
    # Parallelize environment rollouts.
    .env_runners(num_env_runners=3)
)
# Construct the actual (PPO) algorithm object from the config.
algo = config.build()
rl_module = algo.get_module()

# Train for n iterations and report results (mean episode rewards).
# Since we have to move at least 19 times in the env to reach the goal and
# each move gives us -0.1 reward (except the last move at the end: +1.0),
# Expect to reach an optimal episode reward of `-0.1*18 + 1.0 = -0.8`.
for i in range(5):
    results = algo.train()
    print(f"Iter: {i}; avg. results={results['env_runners']}")

# Perform inference (action computations) based on given env observations.
# Note that we are using a slightly different env here (len 10 instead of 20),
# however, this should still work as the agent has (hopefully) learned
# to "just always walk right!"
env = SimpleCorridor({"corridor_length": 10})
# Get the initial observation (should be: [0.0] for the starting position).
obs, info = env.reset()
terminated = truncated = False
total_reward = 0.0
# Play one episode.
while not terminated and not truncated:
    # Compute a single action, given the current observation
    # from the environment.
    action_logits = rl_module.forward_inference(
        {"obs": torch.from_numpy(obs).unsqueeze(0)}
    )["action_dist_inputs"].numpy()[
        0
    ]  # [0]: B=1
    action = np.argmax(action_logits)
    # Apply the computed action in the environment.
    obs, reward, terminated, truncated, info = env.step(action)
    # Sum up rewards for reporting purposes.
    total_reward += reward
# Report results.
print(f"Played 1 episode; total-reward={total_reward}")
# __quick_start_end__
