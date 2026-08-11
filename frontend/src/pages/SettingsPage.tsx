import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Form, Input, Select, Space, Tag, message } from "antd";
import { ApiOutlined, SaveOutlined } from "@ant-design/icons";
import api from "../api/client";

interface LLMSettings {
  provider: "deepseek" | "moonshot";
  base_url: string;
  model: string;
  has_key: boolean;
  providers: {
    deepseek: { base_url: string; model: string; has_key: boolean };
    moonshot: { base_url: string; model: string; has_key: boolean };
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
    load().catch(() => message.error("Failed to load settings"));
  }, [load]);

  const provider = Form.useWatch("provider", form);

  useEffect(() => {
    if (!settings || !provider) return;
    const selected = settings.providers[provider as "deepseek" | "moonshot"];
    form.setFieldsValue({ base_url: selected.base_url, model: selected.model, api_key: "" });
  }, [provider, settings, form]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const { data } = await api.put("/api/settings/llm", values);
      setSettings(data);
      form.setFieldValue("api_key", "");
      message.success("LLM settings saved");
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    try {
      const { data } = await api.post("/api/settings/llm/test");
      message.success(`Connection ok: ${data.reply || "OK"}`);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Connection failed");
    } finally {
      setTesting(false);
    }
  };

  const providerStatus = settings?.providers?.[provider as "deepseek" | "moonshot"];

  return (
    <div style={{ padding: "12px 0", maxWidth: 760 }}>
      <Card title="LLM Provider Settings">
        <Alert
          type="info"
          showIcon
          message="Keys are written to local .env and never returned to the browser after saving."
          style={{ marginBottom: 20 }}
        />
        <Form form={form} layout="vertical">
          <Form.Item name="provider" label="Provider" rules={[{ required: true }]}>
            <Select
              options={[
                { label: "DeepSeek", value: "deepseek" },
                { label: "Kimi / Moonshot", value: "moonshot" },
              ]}
            />
          </Form.Item>
          <Space style={{ marginBottom: 16 }}>
            <Tag color={providerStatus?.has_key ? "green" : "orange"}>
              {providerStatus?.has_key ? "API key configured" : "API key missing"}
            </Tag>
            {settings && <Tag>Current: {settings.provider} / {settings.model}</Tag>}
          </Space>
          <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="model" label="Model" rules={[{ required: true }]}>
            <Input placeholder="deepseek-chat or kimi-k3" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder="Leave blank to keep existing key" />
          </Form.Item>
          <Space>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={save}>Save</Button>
            <Button icon={<ApiOutlined />} loading={testing} onClick={test}>Test current provider</Button>
          </Space>
        </Form>
      </Card>
    </div>
  );
}
