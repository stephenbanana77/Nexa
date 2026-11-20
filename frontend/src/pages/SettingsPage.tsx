import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Form, Input, Select, Space, Tag, message } from "antd";
import { ApiOutlined, SaveOutlined } from "@ant-design/icons";
import api from "../api/client";

interface LLMSettings {
  provider: "deepseek" | "moonshot" | "custom";
  base_url: string;
  model: string;
  has_key: boolean;
  providers: {
    deepseek: { base_url: string; model: string; has_key: boolean };
    moonshot: { base_url: string; model: string; has_key: boolean };
    custom: { base_url: string; model: string; has_key: boolean };
  };
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    const { data } = await api.get("/api/settings/llm");
    setSettings(data);
    form.setFieldsValue({
      provider: data.provider,
      base_url: data.base_url,
      model: data.model,
      api_key: "",
    });
  }, [form]);

  useEffect(() => {
    load().catch(() => message.error("模型设置加载失败，请刷新页面重试"));
  }, [load]);

  const provider = Form.useWatch("provider", form);

  useEffect(() => {
    if (!settings || !provider) return;
    const selected = settings.providers[provider as "deepseek" | "moonshot" | "custom"];
    form.setFieldsValue({ base_url: selected.base_url, model: selected.model, api_key: "" });
  }, [provider, settings, form]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const { data } = await api.put("/api/settings/llm", values);
      setSettings(data);
      form.setFieldValue("api_key", "");
      message.success("模型设置已保存");
    } catch (err: any) {
      message.error(err.response?.data?.detail || "模型设置保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    try {
      const { data } = await api.post("/api/settings/llm/test");
      message.success(`连接成功：${data.reply || "正常"}`);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "连接失败，请检查地址、模型和 API Key");
    } finally {
      setTesting(false);
    }
  };

  const providerStatus = settings?.providers?.[provider as "deepseek" | "moonshot" | "custom"];

  return (
    <div style={{ padding: "12px 0", maxWidth: 760 }}>
      <Card title="模型服务设置">
        <Alert
          type="info"
          showIcon
          message="这是本机全局设置，仅首位注册的工作区管理员可修改。API Key 写入本地 .env，保存后不会返回浏览器。"
          style={{ marginBottom: 20 }}
        />
        <Form form={form} layout="vertical">
          <Form.Item name="provider" label="服务商" rules={[{ required: true }]}>
            <Select
              options={[
                { label: "DeepSeek", value: "deepseek" },
                { label: "Kimi / Moonshot", value: "moonshot" },
                { label: "OpenAI 兼容服务 / 中转站", value: "custom" },
              ]}
            />
          </Form.Item>
          <Space style={{ marginBottom: 16 }}>
            <Tag color={providerStatus?.has_key ? "green" : "orange"}>
              {providerStatus?.has_key ? "已配置 API Key" : "缺少 API Key"}
            </Tag>
            {settings && <Tag>当前：{settings.provider} / {settings.model}</Tag>}
          </Space>
          <Form.Item name="base_url" label="接口地址" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="model" label="模型" rules={[{ required: true }]}>
            <Input placeholder="例如 deepseek-chat、kimi-k3 或中转站模型名" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder="留空则保留已有 Key" />
          </Form.Item>
          <Space>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={save}>保存</Button>
            <Button icon={<ApiOutlined />} loading={testing} onClick={test}>测试当前连接</Button>
          </Space>
        </Form>
      </Card>
    </div>
  );
}
