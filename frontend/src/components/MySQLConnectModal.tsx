import { useState } from "react";
import { Modal, Form, Input, InputNumber, Button, message } from "antd";
import { DatabaseOutlined } from "@ant-design/icons";
import api from "../api/client";

interface Props {
  projectId: string;
  open: boolean;
  onClose: () => void;
  onConnected: (data: any) => void;
}

export default function MySQLConnectModal({ projectId, open, onClose, onConnected }: Props) {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleConnect = async (values: any) => {
    setLoading(true);
    try {
      const { data } = await api.post("/api/datasets/connect-mysql", {
        project_id: projectId,
        ...values,
      });
      message.success(`Connected to ${values.database} (${data.tables?.length || 0} tables)`);
      onConnected(data);
      onClose();
      form.resetFields();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Connection failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Connect MySQL Database"
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={handleConnect}>
        <Form.Item name="host" label="Host" rules={[{ required: true }]} initialValue="localhost">
          <Input placeholder="localhost" />
        </Form.Item>
        <Form.Item name="port" label="Port" initialValue={3306}>
          <InputNumber min={1} max={65535} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="user" label="User" rules={[{ required: true }]} initialValue="root">
          <Input placeholder="root" />
        </Form.Item>
        <Form.Item name="password" label="Password">
          <Input.Password placeholder="Password" />
        </Form.Item>
        <Form.Item name="database" label="Database" rules={[{ required: true }]}>
          <Input placeholder="my_database" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block icon={<DatabaseOutlined />}>
          Connect
        </Button>
      </Form>
    </Modal>
  );
}
