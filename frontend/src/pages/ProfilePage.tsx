import { useState } from 'react';
import { Form, Input, Button, Card, Typography, App } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { authAPI } from '../api/auth';

const { Title } = Typography;

export function ProfilePage() {
  const [loading, setLoading] = useState(false);
  const { message } = App.useApp();

  const onFinish = async (values: { old_password: string; new_password: string }) => {
    setLoading(true);
    try {
      await authAPI.changePassword(values.old_password, values.new_password);
      message.success('密码修改成功');
    } catch (err: any) {
      message.error(err.response?.data?.detail || '修改失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 500, margin: '0 auto' }}>
      <Card title={<Title level={4}>个人中心 - 修改密码</Title>} style={{ borderRadius: 12 }}>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="输入原密码" />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6, message: '新密码至少 6 位' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="输入新密码" />
          </Form.Item>
          <Form.Item
            name="confirm"
            label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="再次输入新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}