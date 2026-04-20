/**
 * Copilot 兼容层
 * 当在 GitHub Copilot 环境中使用时，提供兼容的接口
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

module.exports = {
  /**
   * 检测是否可以在 Copilot 环境中运行
   */
  canHandle: (context) => {
    return context.platform === 'copilot' || context.platform === 'github-copilot';
  },

  /**
   * 处理知识回流请求
   */
  handle: async (params) => {
    const { source, timeRange, keywords, outputFormat } = params;

    try {
      // 检查 lark-cli 是否可用
      const larkCLI = await checkLarkCLI();
      if (!larkCLI) {
        throw new Error('飞书 CLI 未安装，请运行: npm install -g @larksuite/cli');
      }

      // 根据来源类型执行相应的操作
      const results = [];

      if (source === 'all' || source === 'meeting') {
        const meetings = await fetchMeetings(timeRange, keywords);
        results.push(...meetings);
      }

      if (source === 'all' || source === 'wiki') {
        const wikis = await fetchWikis(timeRange, keywords);
        results.push(...wikis);
      }

      if (source === 'all' || source === 'im') {
        const messages = await fetchMessages(timeRange, keywords);
        results.push(...messages);
      }

      // 格式化输出
      return formatOutput(results, outputFormat);

    } catch (error) {
      throw new Error(`知识回流失败: ${error.message}`);
    }
  }
};

/**
 * 检查飞书 CLI 是否已安装
 */
async function checkLarkCLI() {
  return new Promise((resolve) => {
    const proc = spawn('lark-cli', ['--version'], {
      stdio: 'pipe'
    });

    proc.on('error', () => resolve(false));
    proc.on('close', (code) => resolve(code === 0));
  });
}

/**
 * 获取会议纪要
 */
async function fetchMeetings(timeRange, keywords) {
  return new Promise((resolve, reject) => {
    const proc = spawn('lark-cli', ['vc', '+list', '--recent', timeRange], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let error = '';

    proc.stdout.on('data', (data) => {
      output += data.toString();
    });

    proc.stderr.on('data', (data) => {
      error += data.toString();
    });

    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(error));
      } else {
        try {
          const data = JSON.parse(output);
          const meetings = data.data || [];

          // 关键词过滤
          const filtered = keywords.length > 0
            ? meetings.filter(m =>
                keywords.some(kw =>
                  m.title?.includes(kw) || m.summary?.includes(kw)
                )
              )
            : meetings;

          resolve(filtered.map(m => ({
            type: 'meeting',
            title: m.title,
            date: m.create_time,
            url: m.url,
            summary: m.summary,
            actionItems: m.action_items
          })));
        } catch (e) {
          reject(new Error(`解析会议数据失败: ${e.message}`));
        }
      }
    });
  });
}

/**
 * 获取 Wiki 更新
 */
async function fetchWikis(timeRange, keywords) {
  // 类似实现
  return [];
}

/**
 * 获取群聊消息
 */
async function fetchMessages(timeRange, keywords) {
  // 类似实现
  return [];
}

/**
 * 格式化输出
 */
function formatOutput(results, format) {
  if (format === 'json') {
    return JSON.stringify(results, null, 2);
  }

  if (format === 'markdown') {
    return results.map(r => {
      let md = `## ${r.title}\n\n`;
      md += `- **类型**: ${r.type}\n`;
      md += `- **日期**: ${r.date}\n`;
      if (r.url) md += `- **链接**: ${r.url}\n`;
      md += `\n${r.summary}\n`;
      return md;
    }).join('\n---\n\n');
  }

  // summary 格式
  return {
    total: results.length,
    byType: results.reduce((acc, r) => {
      acc[r.type] = (acc[r.type] || 0) + 1;
      return acc;
    }, {}),
    items: results
  };
}
