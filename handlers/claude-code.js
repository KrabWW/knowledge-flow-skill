/**
 * Claude Code 原生处理器
 * 在 Claude Code 环境中提供更好的集成
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

module.exports = {
  /**
   * 在 Claude Code 中处理知识回流
   */
  async process(params) {
    const { source, timeRange, keywords, outputFormat } = params;
    const projectRoot = process.cwd();

    console.log(`\n📥 知识回流开始...`);
    console.log(`   来源: ${source}`);
    console.log(`   时间范围: ${timeRange}`);
    console.log(`   关键词: ${keywords.join(', ') || '无'}\n`);

    // 创建知识目录
    const knowledgeDir = path.join(projectRoot, '.knowledge');
    ensureDir(knowledgeDir);
    ensureDir(path.join(knowledgeDir, 'meetings'));
    ensureDir(path.join(knowledgeDir, 'wiki'));
    ensureDir(path.join(knowledgeDir, 'decisions'));
    ensureDir(path.join(knowledgeDir, 'action-items'));

    // 执行回流
    const results = [];

    if (source === 'all' || source === 'meeting') {
      const meetings = await fetchAndSaveMeetings(timeRange, keywords, knowledgeDir);
      results.push(...meetings);
    }

    if (source === 'all' || source === 'wiki') {
      const wikis = await fetchAndSaveWikis(timeRange, keywords, knowledgeDir);
      results.push(...wikis);
    }

    if (source === 'all' || source === 'im') {
      const messages = await fetchAndSaveMessages(timeRange, keywords, knowledgeDir);
      results.push(...messages);
    }

    // 更新项目摘要
    await updateProjectSummary(projectRoot, results);

    console.log(`\n✅ 知识回流完成! 共处理 ${results.length} 条内容\n`);
    console.log(`   📁 保存位置: ${knowledgeDir}\n`);

    return results;
  }
};

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function fetchAndSaveMeetings(timeRange, keywords, knowledgeDir) {
  try {
    console.log('📹 获取会议纪要...');

    const output = execSync(
      `lark-cli vc +list --recent ${timeRange} --format json`,
      { encoding: 'utf-8' }
    );

    const data = JSON.parse(output);
    const meetings = data.data || [];

    const filtered = keywords.length > 0
      ? meetings.filter(m =>
          keywords.some(kw =>
            m.title?.includes(kw) || m.summary?.includes(kw)
          )
        )
      : meetings;

    // 保存到文件
    filtered.forEach(meeting => {
      const filename = `${meeting.create_time}-${sanitizeTitle(meeting.title)}.md`;
      const filepath = path.join(knowledgeDir, 'meetings', filename);

      const content = `# ${meeting.title}

**日期**: ${new Date(meeting.create_time).toLocaleString('zh-CN')}
**链接**: ${meeting.url}

## 摘要

${meeting.summary}

## 待办事项

${meeting.action_items?.map(item => `- [ ] ${item}`).join('\n') || '无'}
`;

      fs.writeFileSync(filepath, content, 'utf-8');
    });

    console.log(`   ✓ 已保存 ${filtered.length} 条会议纪要`);

    return filtered.map(m => ({
      type: 'meeting',
      title: m.title,
      date: m.create_time,
      file: path.join('.knowledge', 'meetings', filename)
    }));

  } catch (error) {
    console.log(`   ⚠ 获取会议纪要失败: ${error.message}`);
    return [];
  }
}

async function fetchAndSaveWikis(timeRange, keywords, knowledgeDir) {
  // TODO: 实现 Wiki 获取逻辑
  return [];
}

async function fetchAndSaveMessages(timeRange, keywords, knowledgeDir) {
  // TODO: 实现消息获取逻辑
  return [];
}

async function updateProjectSummary(projectRoot, results) {
  const readmePath = path.join(projectRoot, 'README.md');

  if (!fs.existsSync(readmePath)) {
    return;
  }

  let readme = fs.readFileSync(readmePath, 'utf-8');

  // 检查是否已有知识回流部分
  const marker = '<!-- knowledge-flow-summary -->';

  if (readme.includes(marker)) {
    // 更新现有部分
    const newSummary = generateSummary(results);
    readme = readme.replace(
      /<!-- knowledge-flow-summary -->[\s\S]*?<!-- \/knowledge-flow-summary -->/,
      `${marker}\n${newSummary}\n<!-- /knowledge-flow-summary -->`
    );
  } else {
    // 添加新部分
    const newSummary = generateSummary(results);
    readme += `\n\n## 知识回流\n\n${marker}\n${newSummary}\n<!-- /knowledge-flow-summary -->\n`;
  }

  fs.writeFileSync(readmePath, readme, 'utf-8');
}

function generateSummary(results) {
  const byType = results.reduce((acc, r) => {
    acc[r.type] = (acc[r.type] || 0) + 1;
    return acc;
  }, {});

  const lines = [];
  lines.push(`最后更新: ${new Date().toLocaleString('zh-CN')}\n`);
  lines.push('**统计**:\n');

  Object.entries(byType).forEach(([type, count]) => {
    const labels = {
      meeting: '会议纪要',
      wiki: 'Wiki 文档',
      im: '群聊消息',
      doc: '飞书文档'
    };
    lines.push(`- ${labels[type] || type}: ${count}`);
  });

  return lines.join('\n');
}

function sanitizeTitle(title) {
  return title
    .replace(/[<>:"/\\|?*]/g, '-')
    .replace(/\s+/g, '-')
    .slice(0, 50);
}
