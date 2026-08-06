import { useState } from 'react';
import { Table, Button, Tag, Popconfirm, App, Space, Typography } from 'antd';
import { DeleteOutlined, FileTextOutlined } from '@ant-design/icons';
import { Document, knowledgeAPI } from '../../api/knowledge';
import dayjs from 'dayjs';

const { Text } = Typography;

interface DocumentListProps {
  documents: Document[];
  loading: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
  onRefresh: () => void;
  onViewChunks: (docId: string) => void;
}

export function DocumentList({
  documents,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onRefresh,
  onViewChunks,
}: DocumentListProps) {
  const { message } = App.useApp();

  const handleDelete = async (id: string) => {
    try {
      await knowledgeAPI.delete(id);
      message.success('文档已删除');
      onRefresh();
    } catch {
      message.error('删除失败');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string, record: Document) => (
        <Space>
          <FileTextOutlined />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 80,
      render: (t: string) => <Tag>{t.toUpperCase()}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (s: number) => formatSize(s),
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const colorMap: Record<string, string> = {
          completed: 'green',
          processing: 'blue',
          failed: 'red',
        };
        const labelMap: Record<string, string> = {
          completed: '完成',
          processing: '处理中',
          failed: '失败',
        };
        return <Tag color={colorMap[s] || 'default'}>{labelMap[s] || s}</Tag>;
      },
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: any, record: Document) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => onViewChunks(record.id)}
            disabled={record.status !== 'completed'}
          >
            分块
          </Button>
          <Popconfirm title="确定删除此文档？删除后无法恢复" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={documents}
      rowKey="id"
      loading={loading}
      pagination={{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showTotal: (t) => `共 ${t} 个文档`,
        onChange: onPageChange,
      }}
    />
  );
}