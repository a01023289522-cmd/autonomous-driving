"""수업 PPO(algorithms/ppo.py)의 시간초과 처리 수정. 수업 코드는 그대로 두고 롤아웃 수집만 바꾼다.

문제 (11/19 GPT 코드 검토, 직접 확인): 수업 코드는 시간초과(truncated)에서 보상에 γ·V(s')를 더하지만 버퍼에는 done=terminated만
저장한다. 시간초과 스텝이 "안 끝남"으로 남아 GAE(utils/buffer.py compute_gae)가 다음 칸, 즉 **다음 에피소드 첫 상태의 가치**를 한 번
더 더하고 advantage도 에피소드 경계를 넘어 섞인다. 갇혀서 시간초과로 끝나는 행동이 실제보다 좋게 학습된다.
수정: γ·V(s') 보정은 그대로 두고, GAE 경계용 done을 terminated or truncated로 저장한다.
"""
from algorithms.ppo import PPO


class PPOFixed(PPO):
    def collect_rollout(self, env, state, logger=None, ep_stats=None):
        obs = state
        finished_returns = []
        self.buffer.clear()
        for _ in range(self.n_steps):
            action, log_prob, value = self.act(obs)
            next_obs, reward, terminated, truncated, _ = env.step(action)
            self.num_timesteps += 1
            ep_stats[0] += reward
            ep_stats[1] += 1
            stored_reward = reward
            if truncated and not terminated:
                stored_reward += self.gamma * self.get_value(next_obs)   # 시간초과: 이어졌다면 받았을 가치 (수업 코드와 같음)
            self.buffer.add(obs, action, log_prob, stored_reward, value,
                            terminated or truncated)                     # 수정: 시간초과에서도 GAE 경계를 끊는다
            if terminated or truncated:
                finished_returns.append(ep_stats[0])
                if logger is not None:
                    logger.log_episode(self.num_timesteps, ep_stats[0], int(ep_stats[1]))
                ep_stats[0], ep_stats[1] = 0.0, 0
                obs, _ = env.reset()
            else:
                obs = next_obs
        return obs, self.get_value(obs), finished_returns
