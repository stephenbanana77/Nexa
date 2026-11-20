import { useState } from "react";
import { Alert, Modal, Form, Input, InputNumber, Button, Select, message } from "antd";
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
  const [tables, setTables] = useState<{ name: string; row_count: number }[]>([]);
  const [connectionValues, setConnectionValues] = useState<any>(null);
  const [form] = Form.useForm();

  const handleConnect = async (values: any) => {
    setLoading(true);
    try {
      const { data } = await api.post("/api/datasets/connect-mysql", {
        project_id: projectId,
        ...values,
      });
      if (data.status === "select_table") {
        setTables(data.tables || []);
        setConnectionValues(values);
        message.success(`连接成功，请选择要接入的表`);
        return;
      }
      message.success(`已接入 ${data.name}`);
      onConnected(data);
      onClose();
      form.resetFields();
      setTables([]);
      setConnectionValues(null);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "连接失败，请检查地址和凭据后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="连接 MySQL 数据库"
      open={open}
      onCancel={() => { setTables([]); setConnectionValues(null); onClose(); }}
      footer={null}
      destroyOnClose
    >
      {tables.length > 0 ? (
        <Form layout="vertical" onFinish={({ table }) => handleConnect({ ...connectionValues, table })}>
          <Alert
            type="warning"
            showIcon
            message="连接仅在本次服务运行期间有效"
            description="服务重启后需要重新连接。Nexa 不会把数据库密码写入数据集记录。"
            style={{ marginBottom: 16 }}
          />
          <Form.Item name="table" label="选择数据表" rules={[{ required: true, message: "请选择数据表" }]}>
            <Select
              placeholder="选择一张表"
              options={tables.map((table) => ({
                value: table.name,
                label: `${table.name}（${table.row_count.toLocaleString()} 行）`,
              }))}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block icon={<DatabaseOutlined />}>
            接入所选数据表
          </Button>
        </Form>
      ) : <Form form={form} layout="vertical" onFinish={handleConnect}>
        <Form.Item name="host" label="主机地址" rules={[{ required: true }]} initialValue="localhost">
          <Input placeholder="localhost" />
        </Form.Item>
        <Form.Item name="port" label="端口" initialValue={3306}>
          <InputNumber min={1} max={65535} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="user" label="用户名" rules={[{ required: true }]} initialValue="root">
          <Input placeholder="root" />
        </Form.Item>
        <Form.Item name="password" label="密码">
          <Input.Password placeholder="数据库密码" />
        </Form.Item>
        <Form.Item name="database" label="数据库" rules={[{ required: true }]}>
          <Input placeholder="my_database" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block icon={<DatabaseOutlined />}>
          测试连接
        </Button>
      </Form>}
    </Modal>
  );
}
