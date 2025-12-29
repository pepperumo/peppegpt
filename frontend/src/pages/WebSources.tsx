import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAdmin } from '@/hooks/useAdmin';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/use-toast';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  MessageSquare,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Globe,
  ArrowLeft,
} from 'lucide-react';

interface WebSource {
  id: string;
  url: string;
  title?: string;
  status: 'pending' | 'crawling' | 'completed' | 'error';
  last_crawled_at: string | null;
  chunks_count: number;
  created_at: string;
  error_message?: string;
}

const getAgentEndpoint = () => {
  const endpoint = import.meta.env.VITE_AGENT_ENDPOINT || 'http://localhost:8001/api/pydantic-agent';
  // Remove the /api/pydantic-agent part to get the base URL
  return endpoint.replace('/api/pydantic-agent', '');
};

export const WebSources = () => {
  const { isAdmin, loading: adminLoading } = useAdmin();
  const { session } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [webSources, setWebSources] = useState<WebSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newUrl, setNewUrl] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [recrawlingId, setRecrawlingId] = useState<string | null>(null);

  const getAuthHeaders = () => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }
    return headers;
  };

  const fetchWebSources = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${getAgentEndpoint()}/api/web-sources`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch web sources');
      }

      const data = await response.json();
      // API returns { sources: [...], total: N } or array directly
      setWebSources(Array.isArray(data) ? data : data.sources || []);
    } catch (error) {
      console.error('Error fetching web sources:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch web sources',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!adminLoading && !isAdmin) {
      navigate('/');
    }
  }, [isAdmin, adminLoading, navigate]);

  useEffect(() => {
    if (isAdmin) {
      fetchWebSources();
    }
  }, [isAdmin]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAddUrl = async () => {
    if (!newUrl.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a URL',
        variant: 'destructive',
      });
      return;
    }

    // Basic URL validation
    try {
      new URL(newUrl);
    } catch {
      toast({
        title: 'Error',
        description: 'Please enter a valid URL',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsAdding(true);
      const response = await fetch(`${getAgentEndpoint()}/api/web-sources`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ url: newUrl.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to add web source');
      }

      const newSource = await response.json();
      setWebSources((prev) => [newSource, ...prev]);
      setNewUrl('');
      setIsAddDialogOpen(false);
      toast({
        title: 'Success',
        description: 'Web source added successfully',
      });
    } catch (error) {
      console.error('Error adding web source:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to add web source',
        variant: 'destructive',
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id);
      const response = await fetch(`${getAgentEndpoint()}/api/web-sources/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error('Failed to delete web source');
      }

      setWebSources((prev) => prev.filter((source) => source.id !== id));
      toast({
        title: 'Success',
        description: 'Web source deleted successfully',
      });
    } catch (error) {
      console.error('Error deleting web source:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete web source',
        variant: 'destructive',
      });
    } finally {
      setDeletingId(null);
    }
  };

  const handleRecrawl = async (id: string) => {
    try {
      setRecrawlingId(id);
      const response = await fetch(`${getAgentEndpoint()}/api/web-sources/${id}/recrawl`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error('Failed to trigger re-crawl');
      }

      const updatedSource = await response.json();
      setWebSources((prev) =>
        prev.map((source) => (source.id === id ? updatedSource : source))
      );
      toast({
        title: 'Success',
        description: 'Re-crawl triggered successfully',
      });
    } catch (error) {
      console.error('Error triggering re-crawl:', error);
      toast({
        title: 'Error',
        description: 'Failed to trigger re-crawl',
        variant: 'destructive',
      });
    } finally {
      setRecrawlingId(null);
    }
  };

  const getStatusBadge = (status: WebSource['status']) => {
    const statusConfig = {
      pending: { className: 'bg-yellow-500 hover:bg-yellow-500', label: 'Pending' },
      crawling: { className: 'bg-blue-500 hover:bg-blue-500', label: 'Crawling' },
      completed: { className: 'bg-green-500 hover:bg-green-500', label: 'Completed' },
      error: { className: 'bg-red-500 hover:bg-red-500', label: 'Error' },
    };

    const config = statusConfig[status] || statusConfig.pending;
    return (
      <Badge className={`${config.className} text-white`}>
        {config.label}
      </Badge>
    );
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
  };

  const truncateUrl = (url: string, maxLength = 50) => {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
  };

  if (adminLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <div className="flex flex-col min-h-screen">
      <div className="border-b">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            <h1 className="text-lg font-semibold">Web Sources</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/admin">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Admin
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/">
                <MessageSquare className="mr-2 h-4 w-4" />
                Back to Chat
              </Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="max-w-[95%] lg:max-w-[1200px] mx-auto">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold">Web Source Management</h2>
            <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-blue-500 hover:bg-blue-600">
                  <Plus className="mr-2 h-4 w-4" />
                  Add URL
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add New Web Source</DialogTitle>
                  <DialogDescription>
                    Enter a URL to crawl and add to your knowledge base.
                  </DialogDescription>
                </DialogHeader>
                <div className="py-4">
                  <Input
                    placeholder="https://example.com/page"
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleAddUrl();
                      }
                    }}
                  />
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setIsAddDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleAddUrl}
                    disabled={isAdding}
                    className="bg-blue-500 hover:bg-blue-600"
                  >
                    {isAdding ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Adding...
                      </>
                    ) : (
                      'Add URL'
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead width="40%">URL</TableHead>
                  <TableHead width="15%">Status</TableHead>
                  <TableHead width="20%">Last Crawled</TableHead>
                  <TableHead width="10%">Chunks</TableHead>
                  <TableHead width="15%">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  Array(3)
                    .fill(0)
                    .map((_, index) => (
                      <TableRow key={`loading-${index}`}>
                        <TableCell>
                          <Skeleton className="h-4 w-full" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-6 w-20" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-4 w-32" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-4 w-12" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-8 w-20" />
                        </TableCell>
                      </TableRow>
                    ))
                ) : webSources.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8">
                      <div className="text-muted-foreground">
                        No web sources found. Click "Add URL" to add your first web source.
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  webSources.map((source) => (
                    <TableRow key={source.id}>
                      <TableCell>
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:underline"
                          title={source.url}
                        >
                          {truncateUrl(source.url)}
                        </a>
                        {source.error_message && source.status === 'error' && (
                          <div className="text-xs text-red-500 mt-1">
                            {source.error_message}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>{getStatusBadge(source.status)}</TableCell>
                      <TableCell>{formatDate(source.last_crawled_at)}</TableCell>
                      <TableCell>{source.chunks_count}</TableCell>
                      <TableCell>
                        <div className="flex space-x-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleRecrawl(source.id)}
                            disabled={
                              recrawlingId === source.id ||
                              source.status === 'crawling'
                            }
                            title="Re-crawl"
                          >
                            {recrawlingId === source.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCw className="h-4 w-4" />
                            )}
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-red-500 hover:text-red-600 hover:border-red-500"
                                disabled={deletingId === source.id}
                                title="Delete"
                              >
                                {deletingId === source.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Trash2 className="h-4 w-4" />
                                )}
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete Web Source</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete this web source? This will also remove all associated document chunks from the knowledge base.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => handleDelete(source.id)}
                                  className="bg-red-500 hover:bg-red-600"
                                >
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebSources;
