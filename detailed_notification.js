
const axios = require("axios");

// 配置 Telegram Bot Token 和 Chat ID
const TG_BOT_TOKEN = process.env.TG_BOT_TOKEN; // 你的 Telegram Bot Token
const TG_USER_ID = process.env.TG_USER_ID; // 你的 Chat ID

// 通知函数
const sendNotification = async (title, details) => {
  if (!TG_BOT_TOKEN || !TG_USER_ID) {
    console.log("请配置 TG_BOT_TOKEN 和 TG_USER_ID 环境变量！");
    return;
  }

  const message = `${title}\n\n详细信息：\n${details}`;
  const url = \`https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage\`;
  const data = { chat_id: TG_USER_ID, text: message };

  try {
    const response = await axios.post(url, data);
    if (response.data.ok) {
      console.log("Telegram 通知发送成功！");
    } else {
      console.error("Telegram 通知发送失败：", response.data);
    }
  } catch (error) {
    console.error("发送 Telegram 通知时出错：", error);
  }
};

// 主任务逻辑
const mainTask = async () => {
  let taskOutput = "";
  try {
    console.log("任务开始执行...");
    taskOutput += "任务开始执行...\n";

    // 模拟任务处理（替换为你的业务逻辑）
    for (let i = 1; i <= 5; i++) {
      taskOutput += \`正在处理第 ${i} 步...\n\`;
      console.log(\`正在处理第 ${i} 步...\`);
      await new Promise((resolve) => setTimeout(resolve, 1000)); // 模拟耗时任务
    }

    console.log("任务执行成功！");
    taskOutput += "任务执行成功！\n";

    // 发送成功通知
    await sendNotification("任务已成功完成！", taskOutput);
  } catch (error) {
    console.error("任务执行失败：", error);
    taskOutput += \`任务执行失败：${error.message}\n\`;

    // 发送失败通知
    await sendNotification("任务失败", taskOutput);
  }
};

// 执行主任务
mainTask();
